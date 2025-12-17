import gmsh
import assembly_mesh_plugin
from tests.sample_assemblies import (
    generate_nested_spheres,
    generate_touching_boxes,
    generate_nested_boxes,
    generate_simple_nested_boxes,
    generate_test_cross_section,
    generate_assembly,
    generate_subshape_assembly,
    generate_materials_assembly,
)


def test_simple_assembly():
    """
    Tests to make sure that the most basic assembly works correctly with tagging.
    """

    # Create the basic assembly
    assy = generate_simple_nested_boxes()

    # Create a mesh that has all the faces tagged as physical groups
    assy.saveToGmsh(mesh_path="tagged_mesh.msh")

    gmsh.initialize()

    gmsh.open("tagged_mesh.msh")

    # Make sure that there are physical groups for the volumes
    physical_groups = gmsh.model.getPhysicalGroups(3)
    assert len(physical_groups) > 0, "There should be some physical groups for volumes"

    # Check the solids for the correct tags
    for group in physical_groups:
        # Get the name for the current volume
        cur_name = gmsh.model.getPhysicalName(3, group[1])

        assert cur_name in ["shell", "insert"]

    # Check to make sure there are physical groups for the surfaces
    physical_groups = gmsh.model.getPhysicalGroups(2)
    assert len(physical_groups) > 0, "There should be some physical groups for surfaces"

    # Check the surfaces for the correct tags
    for group in physical_groups:
        # Get the name for this group
        cur_name = gmsh.model.getPhysicalName(2, group[1])

        # Skip any groups that are not tagged explicitly
        if "_surface_" in cur_name:
            continue

        assert cur_name in ["shell_inner-right", "insert_outer-right", "in_contact"]


def test_subshape_assembly():
    """
    Tests whether subshapes in assemblies get exported to physical groups in the resulting mesh.
    """

    # Generate a simple assembly with a subshape
    assy = generate_subshape_assembly()

    # Create a mesh that has all the faces tagged as physical groups
    assy.saveToGmsh(mesh_path="tagged_subshape_mesh.msh")

    gmsh.initialize()

    gmsh.open("tagged_subshape_mesh.msh")

    # Make sure that there are physical groups for the volumes
    physical_groups = gmsh.model.getPhysicalGroups(3)
    assert len(physical_groups) > 0, "There should be some physical groups for volumes"

    # Check the solids/volumes for the correct tags
    for group in physical_groups:
        # Get the name for the current volume
        cur_name = gmsh.model.getPhysicalName(3, group[1])

        assert cur_name in ["cube_1"]

    # Check to make sure there are physical groups for the surfaces
    physical_groups = gmsh.model.getPhysicalGroups(2)
    assert len(physical_groups) > 0, "There should be some physical groups for surfaces"

    # Check the surfaces for the correct tags
    for group in physical_groups:
        # Get the name for this group
        cur_name = gmsh.model.getPhysicalName(2, group[1])

        # Skip any groups that are not tagged explicitly
        if "_surface_" in cur_name:
            continue

        assert cur_name in ["cube_1_cube_1_top_face"]


def test_imprinted_assembly():
    # Create the basic assembly
    assy = generate_simple_nested_boxes()

    assy.assemblyToImprintedGmsh("tagged_imprinted_mesh.msh")

    gmsh.initialize()

    gmsh.open("tagged_imprinted_mesh.msh")

    # Make sure that there are physical groups for the volumes
    physical_groups = gmsh.model.getPhysicalGroups(3)
    assert len(physical_groups) > 0, "There should be some physical groups for volumes"

    # Check the solids for the correct tags
    for group in physical_groups:
        # Get the name for the current volume
        cur_name = gmsh.model.getPhysicalName(3, group[1])

        assert cur_name in ["shell", "insert"]

    # Check to make sure there are physical groups for the surfaces
    physical_groups = gmsh.model.getPhysicalGroups(2)
    assert len(physical_groups) > 0, "There should be some physical groups for surfaces"

    # Check the surfaces for the correct tags
    for group in physical_groups:
        # Get the name for this group
        cur_name = gmsh.model.getPhysicalName(2, group[1])

        # Skip any groups that are not tagged explicitly
        if "_surface_" in cur_name:
            continue

        assert cur_name in ["shell_inner-right", "insert_outer-right", "in_contact"]


def test_nested_sphere_assembly():
    """
    Tests to make sure the the nested sphere example works.
    """

    def _check_physical_groups():
        # Make sure that there are physical groups for the volumes
        physical_groups = gmsh.model.getPhysicalGroups(3)
        assert (
            len(physical_groups) == 2
        ), "There should be two physical groups for volumes"

        # Check the solids for the correct tags
        for group in physical_groups:
            # Get the name for the current volume
            cur_name = gmsh.model.getPhysicalName(3, group[1])

            assert cur_name in ["inner_sphere", "middle_sphere"]

        # Make sure we can retrieve the physical groups
        inner_sphere_volume = gmsh.model.getEntitiesForPhysicalName("inner_sphere")
        middle_sphere_volume = gmsh.model.getEntitiesForPhysicalName("middle_sphere")

    # Create a basic assembly
    assy = generate_nested_spheres()

    #
    # Go through the entire process with an imprinted assembly.
    #
    gmsh = assy.getGmsh(imprint=True)
    gmsh.model.mesh.generate(3)

    # Ensure that there are physical groups and that they have the right names
    _check_physical_groups()

    #
    # Go othrough the entire process again with a non-imprinted assembly.
    #
    gmsh = assy.getGmsh(imprint=False)
    gmsh.model.mesh.generate(3)

    # Ensure that there are physical groups
    _check_physical_groups()


def test_mesh_materials():
    """
    Tests to make sure that assembly materials are preserved in the mesh data.
    """

    # Create the basic assembly with materials
    assy = generate_materials_assembly()

    #
    # Imprinted assembly
    #
    gmsh = assy.getGmsh(imprint=True)
    gmsh.model.mesh.generate(3)

    phys_groups = gmsh.model.getPhysicalGroups(3)

    # Make sure we got the correct names
    name = gmsh.model.getPhysicalName(3, 1)
    assert name == "cube_1"
    name = gmsh.model.getPhysicalName(3, 2)
    assert name == "mat:copper"
    name = gmsh.model.getPhysicalName(3, 3)
    assert name == "cube_2"
    name = gmsh.model.getPhysicalName(3, 4)
    assert name == "mat:steel"

    #
    # Non-imprinted assembly
    #
    gmsh = assy.getGmsh(imprint=False)
    gmsh.model.mesh.generate(3)

    phys_groups = gmsh.model.getPhysicalGroups(3)

    # Make sure we got the correct names
    name = gmsh.model.getPhysicalName(3, 1)
    assert name == "cube_1"
    name = gmsh.model.getPhysicalName(3, 2)
    assert name == "mat:copper"
    name = gmsh.model.getPhysicalName(3, 3)
    assert name == "cube_2"
    name = gmsh.model.getPhysicalName(3, 4)
    assert name == "mat:steel"
