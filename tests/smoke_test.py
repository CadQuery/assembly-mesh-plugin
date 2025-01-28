import assembly_mesh_plugin.plugin
from tests.sample_assemblies import (
    generate_simple_nested_boxes,
    generate_test_cross_section,
    generate_assembly,
)


def test_basic_assembly():
    """
    Tests to make sure that the most basic assembly works correctly with tagging.
    """

    # Create the basic assembly
    assy = generate_simple_nested_boxes()

    # Create a mesh that has all the faces tagged as physical groups
    assy.assemblyToGmsh(mesh_path="tagged_mesh.msh")


def test_basic_cross_section():
    """
    Tests to make sure that tagging works correctly between a simple CadQuery assembly and Gmsh.
    """

    # Create the cross-section assembly
    assy = generate_test_cross_section()

    # Create a mesh that has all the faces in the correct physical groups
    assy.assemblyToGmsh(mesh_path="tagged_cross_section.msh")


def test_planar_coil():
    """
    Test to make sure a full coil that has a centroid that is planar works with tagging correctly.
    """

    # Create the planar coil assembly
    assy = generate_assembly()

    # Create a mesh that has all the faces in the correct physical groups
    assy.assemblyToGmsh(mesh_path="tagged_planar_coil.msh")
