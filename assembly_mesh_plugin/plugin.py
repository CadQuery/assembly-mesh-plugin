import tempfile

from OCP.TopoDS import TopoDS_Shape
import cadquery as cq
import gmsh

# The mesh volume and surface ids should line up with the order of solids and faces in the assembly
vol_id = 1
surface_id = 1

volumes = {}
volume_map = {}

# Holds the collection of individual faces that are tagged
tagged_faces = {}

# Holds the collection of individual edges that are tagged
tagged_edges = {}

# Tracks which gmsh curve tags belong to each part
solid_curves = {}

# Tracks multi-surface physical groups
multi_material_groups = {}
surface_groups = {}

# Tracks edge (1D) physical groups
edge_groups = {}
multi_material_edge_groups = {}


def _gmsh_curve_signatures(gmsh):
    """
    Build a geometric signature for every 1D curve currently in the model, keyed
    by gmsh curve tag. Matching tagged edges by geometry rather than enumeration
    order keeps edge tagging correct even when curves are shared between faces/solids.
    """
    sigs = {}
    for _, ctag in gmsh.model.getEntities(1):
        bbox = gmsh.model.getBoundingBox(1, ctag)
        tmin, tmax = gmsh.model.getParametrizationBounds(1, ctag)
        mid = gmsh.model.getValue(1, ctag, [0.5 * (tmin[0] + tmax[0])])
        sigs[ctag] = (bbox, mid)

    return sigs


def _edge_matches(edge, sig, tol=1e-6):
    """True if a CadQuery edge matches a gmsh curve signature."""
    bbox, mid = sig
    eb = edge.BoundingBox()
    cqbox = (eb.xmin, eb.ymin, eb.zmin, eb.xmax, eb.ymax, eb.zmax)
    if max(abs(a - b) for a, b in zip(cqbox, bbox)) > tol:
        return False

    # Midpoint disambiguates curves that share a bounding box
    em = edge.positionAt(0.5)
    return (
        abs(em.x - mid[0]) <= tol
        and abs(em.y - mid[1]) <= tol
        and abs(em.z - mid[2]) <= tol
    )


def extract_subshape_names(assy, name=None):
    """
    Extracts any subshape names from the current assembly.
    """
    global tagged_faces

    # We only want the last part of the name parent path
    short_name = name.split("/")[-1]

    # Try extracting via names and layers
    if assy._subshape_names or assy._subshape_layers:
        # Make sure the entry for the assembly child exists
        if short_name not in tagged_faces:
            tagged_faces[short_name] = {}

        # Step through the subshape names and layers together
        combined_subshapes = assy._subshape_names | assy._subshape_layers
        for subshape, subshape_tag in combined_subshapes.items():
            # Create a new list for tag if it does not already exist
            if subshape_tag in tagged_faces[short_name]:
                tagged_faces[short_name][subshape_tag].append(subshape)
            else:
                tagged_faces[short_name][subshape_tag] = [subshape]

    # Check for face and edge tags
    if assy.objects[short_name].obj:
        for tag, wp in assy.objects[short_name].obj.ctx.tags.items():
            # Make sure the entries for the assembly child exists
            tagged_faces.setdefault(short_name, {})
            tagged_edges.setdefault(short_name, {})

            # A tag stores a Workplane object that can contain edges or faces
            objs = wp.objects
            if objs and isinstance(objs[0], cq.Edge):
                for edge in wp.edges().all():
                    tagged_edges[short_name].setdefault(tag, []).append(edge.val())
            else:
                for face in wp.faces().all():
                    tagged_faces[short_name].setdefault(tag, []).append(face.val())

    # Recurse through the assembly children
    for child in assy.children:
        extract_subshape_names(child, child.name)


def add_solid_to_mesh(gmsh, solid, name):
    """
    Adds a given CadQuery solid to the gmsh mesh.
    """
    global vol_id, volumes, volume_map

    before = {t for _, t in gmsh.model.getEntities(1)}

    with tempfile.NamedTemporaryFile(suffix=".brep") as temp_file:
        solid.exportBrep(temp_file.name)
        dim_tags = gmsh.model.occ.importShapes(temp_file.name)

        for dim, tag in dim_tags:
            # We only want volumes in this pass
            if dim == 3:
                # Initialize the list holding the volume entities, if needed
                if tag in volumes.keys():
                    volumes[tag].append((3, tag))
                else:
                    volumes[tag] = []
                    volumes[tag].append((3, tag))
                volume_map[tag] = name

                # Move to the next volume ID
                vol_id += 1

    gmsh.model.occ.synchronize()
    after = {t for _, t in gmsh.model.getEntities(1)}
    solid_curves.setdefault(name, set()).update(after - before)


def add_faces_to_mesh(gmsh, solid, name, loc=None):
    global surface_id, multi_material_groups, surface_groups

    # If the current solid has no tagged faces, there is nothing to do
    if name not in tagged_faces.keys():
        return

    # All the faces in the current part should be added to the mesh
    for face in solid.Faces():
        # Face name can be based on a tag, or just be a generic name
        found_tag = False

        #
        # Handle tagged faces
        # Step through the faces in the solid and check them against all the tagged faces
        #
        for tag, tag_faces in tagged_faces[name].items():
            for tag_face in tag_faces:
                # Move the face to the correct location in the assembly
                if loc:
                    tag_face = tag_face.moved(loc)

                # If OpenCASCADE says the faces are the same, we have a match for the tag
                if TopoDS_Shape.IsEqual(face.wrapped, tag_face.wrapped):
                    # Make sure a generic surface is not added for this face
                    found_tag = True

                    # Find out if this is a multi-material tag
                    if tag.startswith("~"):
                        # Set the surface name to be the name of the tag without the ~
                        group_name = tag.replace("~", "").split("-")[0]

                        # Add this face to the multi-material group
                        if group_name in multi_material_groups:
                            multi_material_groups[group_name].append(surface_id)
                        else:
                            multi_material_groups[group_name] = [surface_id]
                    else:
                        # We want to track all surfaces that might be in a tag group
                        cur_tag_name = f"{name}_{tag}"
                        if cur_tag_name in surface_groups:
                            surface_groups[cur_tag_name].append(surface_id)
                        else:
                            surface_groups[cur_tag_name] = [surface_id]

        # If the solid does not have any tagged faces, add them to a generic physical group
        if not found_tag:
            # Generate a unique name for the surface and set it on the physical group
            face_name = f"{name}_surface_{surface_id}"
            ps = gmsh.model.addPhysicalGroup(2, [surface_id])
            gmsh.model.setPhysicalName(2, ps, f"{face_name}")
            gmsh.model.occ.synchronize()

        # Make sure to move to the next surface ID
        surface_id += 1

    gmsh.model.occ.synchronize()


def add_edges_to_mesh(gmsh, name, loc=None, curve_sigs=None):
    """Match a part's tagged edges to gmsh curves and collect them into 1D physical groups."""
    global edge_groups, multi_material_edge_groups

    if not tagged_edges.get(name):
        return

    for tag, tag_edges in tagged_edges[name].items():
        for tag_edge in tag_edges:
            # Move the edge into its assembly position
            if loc:
                tag_edge = tag_edge.moved(loc)

            # Find the gmsh curve whose geometry matches this tagged edge
            match = next(
                (c for c, sig in curve_sigs.items() if _edge_matches(tag_edge, sig)),
                None,
            )
            if match is None:
                continue

            # Same ~ convention as faces: strip the part name for multi-part groups
            if tag.startswith("~"):
                group_name = tag.replace("~", "").split("-")[0]
                multi_material_edge_groups.setdefault(group_name, []).append(match)
            else:
                edge_groups.setdefault(f"{name}_{tag}", []).append(match)


def get_gmsh(self, imprint=True):
    """
    Allows the user to get a gmsh object from the assembly, respecting assembly part names and face
    tags, but have more control over how it is meshed. This method makes sure the mesh is conformal.
    """
    global vol_id, surface_id, volumes, volume_map, tagged_faces, multi_material_groups, surface_groups, solid_curves, tagged_edges, edge_groups, multi_material_edge_groups

    # Reset global state for each call
    vol_id = 1
    surface_id = 1
    volumes = {}
    volume_map = {}
    tagged_faces = {}
    multi_material_groups = {}
    surface_groups = {}
    solid_materials = []
    solid_curves = {}
    tagged_edges = {}
    edge_groups = {}
    multi_material_edge_groups = {}

    gmsh.initialize()
    gmsh.option.setNumber(
        "General.Terminal", 0
    )  # Make sure this is 0 for production for clean stdout
    gmsh.model.add("assembly")

    # Get all of the subshapes and their corresponding names/positions
    extract_subshape_names(self, self.name)

    # Handle the imprinted assembly
    if imprint:
        # Imprint the assembly
        imprinted_assembly, imprinted_solids_with_orginal_ids = (
            cq.occ_impl.assembly.imprint(self)
        )

        # Collect the materials
        for imp_solid, solid_id in imprinted_solids_with_orginal_ids.items():
            # Track down the original assembly object so that we can retrieve materials, if present
            short_id = solid_id[0].split("/")[-1] if "/" in solid_id[0] else solid_id[0]
            subassy = self.objects[short_id]

            # Save the assembly material associated with this solid
            if subassy.material:
                solid_materials.append(subassy.material.name)

        for solid, name in imprinted_solids_with_orginal_ids.items():
            # Get just the name of the current assembly
            short_name = name[0].split("/")[-1]

            # Add the current solid to the mesh
            add_solid_to_mesh(gmsh, solid, short_name)

            # Add faces to the mesh and handle tagged faces
            add_faces_to_mesh(gmsh, solid, short_name, None)

    # Handle the non-imprinted assembly
    else:
        # Step through all of the solids in the assembly
        for obj, name, loc, _ in self:
            # Get just the name of the current assembly
            short_name = name.split("/")[-1]

            for solid in obj.moved(loc).Solids():
                # Add the current solid to the mesh
                add_solid_to_mesh(gmsh, solid, short_name)

                # Add faces to the mesh and handle tagged faces
                add_faces_to_mesh(gmsh, solid, short_name, loc)

            # Keep track of the materials
            if self.objects[name.split("/")[-1]].material:
                solid_materials.append(self.objects[name.split("/")[-1]].material.name)

    # Second pass: Build the curve signatures once and match each part's tagged edges
    # against only the curves that belong to that part.
    gmsh.model.occ.synchronize()
    curve_sigs = _gmsh_curve_signatures(gmsh)

    if imprint:
        seen = set()
        for _, name in imprinted_solids_with_orginal_ids.items():
            short_name = name[0].split("/")[-1]
            if short_name in seen:
                continue
            seen.add(short_name)
            part_sigs = {c: curve_sigs[c] for c in solid_curves.get(short_name, ())}
            add_edges_to_mesh(gmsh, short_name, None, part_sigs)
    else:
        for obj, name, loc, _ in self:
            short_name = name.split("/")[-1]
            part_sigs = {c: curve_sigs[c] for c in solid_curves.get(short_name, ())}
            add_edges_to_mesh(gmsh, short_name, loc, part_sigs)

    # Step through each of the volumes and add physical groups for each
    for volume_id in volumes.keys():
        gmsh.model.occ.synchronize()

        # Attach the name to the volume
        ps = gmsh.model.addPhysicalGroup(3, volumes[volume_id][0])
        gmsh.model.setPhysicalName(3, ps, f"{volume_map[volume_id]}")

        # Attach the material to the volume, if the material is present
        if len(solid_materials) >= volume_id:
            ps1 = gmsh.model.addPhysicalGroup(3, volumes[volume_id][0])
            gmsh.model.setPhysicalName(3, ps1, f"mat:{solid_materials[volume_id - 1]}")

    # Handle tagged surface groups
    for t_name, surf_group in surface_groups.items():
        gmsh.model.occ.synchronize()
        ps = gmsh.model.addPhysicalGroup(2, surf_group)
        gmsh.model.setPhysicalName(2, ps, t_name)

    # Handle multi-material tags
    for group_name, mm_group in multi_material_groups.items():
        gmsh.model.occ.synchronize()
        ps = gmsh.model.addPhysicalGroup(2, mm_group)
        gmsh.model.setPhysicalName(2, ps, f"{group_name}")

    # Handle tagged edge groups (1D physical groups)
    for e_name, edge_group in edge_groups.items():
        gmsh.model.occ.synchronize()
        ps = gmsh.model.addPhysicalGroup(1, edge_group)
        gmsh.model.setPhysicalName(1, ps, e_name)

    # Handle multi-material edge tags
    for group_name, mm_group in multi_material_edge_groups.items():
        gmsh.model.occ.synchronize()
        ps = gmsh.model.addPhysicalGroup(1, mm_group)
        gmsh.model.setPhysicalName(1, ps, f"{group_name}")

    gmsh.model.occ.synchronize()

    return gmsh


def get_tagged_gmsh(self):
    """
    Allows the user to get a gmsh object from the assembly, respecting assembly part names and face
    tags, but have more control over how it is meshed.
    """

    gmsh = get_gmsh(self, imprint=False)

    return gmsh


def get_imprinted_gmsh(self):
    """
    Allows the user to get a gmsh object from the assembly, with the assembly being imprinted.
    """

    gmsh = get_gmsh(self, imprint=True)

    return gmsh


def assembly_to_gmsh(self, mesh_path="tagged_mesh.msh"):
    """
    Pack the assembly into a gmsh object, respecting assembly part names and face tags when creating
    the physical groups.
    """

    # Turn this assembly with potentially tagged faces into a gmsh object
    gmsh = get_tagged_gmsh(self)

    gmsh.model.mesh.field.setAsBackgroundMesh(2)

    gmsh.model.mesh.generate(3)
    gmsh.write(mesh_path)

    gmsh.finalize()


def assembly_to_imprinted_gmsh(self, mesh_path="tagged_mesh.msh"):
    """
    Exports an imprinted assembly to capture conformal meshes.
    """

    # Turn this assembly into a imprinted gmsh object
    gmsh = get_imprinted_gmsh(self)

    gmsh.model.mesh.field.setAsBackgroundMesh(2)

    gmsh.model.mesh.generate(3)
    gmsh.write(mesh_path)

    gmsh.finalize()


# Patch the new assembly functions into CadQuery's importers package
cq.Assembly.assemblyToGmsh = assembly_to_gmsh
cq.Assembly.saveToGmsh = assembly_to_gmsh  # Alias name that works better on cq.Assembly
cq.Assembly.assemblyToImprintedGmsh = assembly_to_imprinted_gmsh
cq.Assembly.getTaggedGmsh = get_tagged_gmsh
cq.Assembly.getImprintedGmsh = get_imprinted_gmsh
cq.Assembly.getGmsh = get_gmsh
