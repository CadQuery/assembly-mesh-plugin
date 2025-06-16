import tempfile

from OCP.TopoDS import TopoDS_Shape
import cadquery as cq
import gmsh


def get_tagged_gmsh(self):
    """
    Allows the user to get a gmsh object from the assembly, respecting assembly part names and face
    tags, but have more control over how it is meshed.
    """
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("coil_assembly")

    # The mesh volume and surface ids should line up with the order of solids and faces in the assembly
    vol_id = 1
    surface_id = 1

    # Tracks multi-surface physical groups
    multi_material_groups = {}
    surface_groups = {}

    # Holds the collection of individual faces that are tagged
    tagged_faces = {}

    for obj, name, loc, _ in self:
        # CadQuery assembly code prepends a UUID to names sometimes that we do not need
        short_name = name.split("/")[-1]

        # Separate tagged faces by solid since they might be duplicates
        tagged_faces[short_name] = {}

        # Extract the tagged faces and make sure they are in the appropriate relative locations
        # in the assembly. Tags can hold multiple faces, so we have to extract all of them.
        for tag, wp in self.objects[short_name].obj.ctx.tags.items():
            for face in wp.faces().all():
                # Check to see if we have found this tag before (multi-material tag)
                if tag in tagged_faces[short_name]:
                    tagged_faces[short_name][tag].append(face.val())
                else:
                    tagged_faces[short_name][tag] = [face.val()]

        # Extract the tagged faces that have been added by the addSubshape method of cq.Assembly
        if self._subshape_names:
            for subshape, subshape_tag in self._subshape_names.items():
                if subshape_tag in tagged_faces[short_name]:
                    # Check to see if this is a duplicate
                    if subshape in tagged_faces[short_name][subshape_tag]:
                        print(
                            f"WARNING: Duplicate subshape found for tag {subshape_tag}."
                        )

                    tagged_faces[short_name][subshape_tag].append(subshape)
                else:
                    tagged_faces[short_name][subshape_tag] = [subshape]

        # Extract the tagged faces that have been added by the addSubshape method of cq.Assembly
        if self._subshape_layers:
            for subshape, subshape_tag in self._subshape_layers.items():
                if subshape_tag in tagged_faces[short_name]:
                    # Check to see if this is a duplicate
                    if subshape in tagged_faces[short_name][subshape_tag]:
                        print(
                            f"WARNING: Duplicate subshape found for tag {subshape_tag}."
                        )

                    tagged_faces[short_name][subshape_tag].append(subshape)
                else:
                    tagged_faces[short_name][subshape_tag] = [subshape]

        # All the solids in the current part should be added to the mesh
        for s in obj.moved(loc).Solids():
            # Add the current solid to the mesh
            with tempfile.NamedTemporaryFile(suffix=".brep") as temp_file:
                s.exportBrep(temp_file.name)
                ps = gmsh.model.occ.importShapes(temp_file.name)

            # TODO find a way to check if the OCC in gmsh is compatible with the
            # OCC in CadQuery. When pip installed they tend to be incompatible
            # and this importShapesNativePointer will seg fault. When both
            # packages are conda installed the importShapesNativePointer works.
            # Work around that works in both cases is to write a brep and import
            # it into gmsh. This is slower but works in all cases.
            # gmsh.model.occ.importShapesNativePointer(s.wrapped._address())

            gmsh.model.occ.synchronize()

            # Technically, importShapes could import multiple entities/dimensions, so filter those
            vol_ents = []
            for p in ps:
                if p[0] == 3:
                    vol_ents.append(p[1])

            # Set the physical name to be the part name in the assembly for all the solids
            ps2 = gmsh.model.addPhysicalGroup(3, vol_ents)
            gmsh.model.setPhysicalName(3, ps2, f"{name.split('/')[-1]}")

            # All the faces in the current part should be added to the mesh
            for face in s.Faces():
                # Face name can be based on a tag, or just be a generic name
                found_tag = False

                #
                # Handle tagged faces
                # Step through the faces in the solid and check them against all the tagged faces
                #
                for tag, tag_faces in tagged_faces[short_name].items():
                    for tag_face in tag_faces:
                        # Move the face to the correct location in the assembly
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
                                cur_tag_name = f"{short_name}_{tag}"
                                if cur_tag_name in surface_groups:
                                    print(
                                        "Append: ", cur_tag_name, short_name, surface_id
                                    )
                                    surface_groups[cur_tag_name].append(surface_id)
                                else:
                                    print("New: ", cur_tag_name, short_name, surface_id)
                                    surface_groups[cur_tag_name] = [surface_id]

                # If no tag was found, set a physical group generic name
                if not found_tag:
                    face_name = f"{short_name}_surface_{surface_id}"
                    ps = gmsh.model.addPhysicalGroup(2, [surface_id])
                    gmsh.model.setPhysicalName(2, ps, f"{face_name}")

                # Move to the next surface id
                surface_id += 1

            # Move to the next volume id
            vol_id += 1

    # Handle tagged surface groups
    for t_name, surf_group in surface_groups.items():
        ps = gmsh.model.addPhysicalGroup(2, surf_group)
        gmsh.model.setPhysicalName(2, ps, t_name)

    # Handle multi-material tags
    for group_name, mm_group in multi_material_groups.items():
        ps = gmsh.model.addPhysicalGroup(2, mm_group)
        gmsh.model.setPhysicalName(2, ps, f"{group_name}")

    gmsh.model.occ.synchronize()

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


def get_imprinted_gmsh(self):
    """
    Allows the user to get a gmsh object from the assembly, with the assembly being imprinted.
    """

    # Initialize gmsh and create a new model
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("assembly")

    # The mesh volume and surface ids should line up with the order of solids and faces in the assembly
    vol_id = 1
    surface_id = 1

    # Tracks multi-surface physical groups
    multi_material_groups = {}
    surface_groups = {}

    # Tracks the solids with tagged faces
    tagged_faces = {}
    solids_with_tagged_faces = {}

    # Imprint the assembly
    imprinted_assembly, imprinted_solids_with_orginal_ids = (
        cq.occ_impl.assembly.imprint(self)
    )

    for solid, id in imprinted_solids_with_orginal_ids.items():
        # Add the current solid to the mesh
        # Work-around for a segfault with in-memory passing of OCCT objects
        with tempfile.NamedTemporaryFile(suffix=".brep") as temp_file:
            solid.exportBrep(temp_file.name)
            ps = gmsh.model.occ.importShapes(temp_file.name)
        gmsh.model.occ.synchronize()

        # Technically, importShapes could import multiple entities/dimensions, so filter those
        vol_ents = []
        for p in ps:
            if p[0] == 3:
                vol_ents.append(p[1])

        # Set the physical name to be the part name in the assembly for all the solids
        ps2 = gmsh.model.addPhysicalGroup(3, vol_ents)
        gmsh.model.setPhysicalName(3, ps2, f"{id[0].split('/')[-1]}")

        # Get the original assembly part
        object_name = id[0].split("/")[-1]
        assembly_part = self.objects[object_name]

        # Collect any tags from the part
        for tag, wp in assembly_part.obj.ctx.tags.items():
            tagged_face = wp.faces().all()[0].val()
            for face in wp.faces().all():
                tagged_faces[face.val()] = tag

        # Iterate over the faces of the assembly part
        for face in assembly_part.obj.faces():
            for tagged_face, tag in tagged_faces.items():
                if TopoDS_Shape.IsEqual(face.wrapped, tagged_face.wrapped):
                    print(f"{vol_id}_{surface_id}", tag)
                    solids_with_tagged_faces[f"{vol_id}_{surface_id}"] = (
                        object_name,
                        tag,
                    )

            surface_id += 1
        vol_id += 1

    # Reset the volume and surface IDs
    vol_id = 1
    surface_id = 1

    # Step through the imprinted assembly/shape and check for tagged faces
    for solid in imprinted_assembly.solids():
        for face in solid.faces().Faces():
            # Check to see if this face has been tagged
            if f"{vol_id}_{surface_id}" in solids_with_tagged_faces.keys():
                short_name = solids_with_tagged_faces[f"{vol_id}_{surface_id}"][0]
                tag = solids_with_tagged_faces[f"{vol_id}_{surface_id}"][1]

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
                    cur_tag_name = f"{short_name}_{tag}"
                    if cur_tag_name in surface_groups:
                        print("Append: ", cur_tag_name, short_name, surface_id)
                        surface_groups[cur_tag_name].append(surface_id)
                    else:
                        print("New: ", cur_tag_name, short_name, surface_id)
                        surface_groups[cur_tag_name] = [surface_id]

            surface_id += 1
        vol_id += 1

    # Handle tagged surface groups
    for t_name, surf_group in surface_groups.items():
        ps = gmsh.model.addPhysicalGroup(2, surf_group)
        gmsh.model.setPhysicalName(2, ps, t_name)

    # Handle multi-material tags
    for group_name, mm_group in multi_material_groups.items():
        ps = gmsh.model.addPhysicalGroup(2, mm_group)
        gmsh.model.setPhysicalName(2, ps, f"{group_name}")

    gmsh.model.occ.synchronize()

    return gmsh


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
cq.Assembly.getTaggedGmsh = get_tagged_gmsh
cq.Assembly.assemblyToImprintedGmsh = assembly_to_imprinted_gmsh
cq.Assembly.getImprintedGmsh = get_imprinted_gmsh
