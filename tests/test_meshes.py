import gmsh
import assembly_mesh_plugin.plugin
from tests.sample_assemblies import (
    generate_nested_boxes,
    generate_simple_nested_boxes,
    generate_test_cross_section,
    generate_assembly,
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

    # Check the solids for the correct tags
    physical_groups = gmsh.model.getPhysicalGroups(3)
    for group in physical_groups:
        # Get the name for the current volume
        cur_name = gmsh.model.getPhysicalName(3, group[1])

        assert cur_name in ["shell", "insert"]

    # Check the surfaces for the correct tags
    physical_groups = gmsh.model.getPhysicalGroups(2)
    for group in physical_groups:
        # Get the name for this group
        cur_name = gmsh.model.getPhysicalName(2, group[1])

        # Skip any groups that are not tagged explicitly
        if "_surface_" in cur_name:
            continue

        assert cur_name in ["shell_inner-right", "insert_outer-right", "in_contact"]
