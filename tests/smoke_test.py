import assembly_mesh_plugin
from tests.sample_assemblies import (
    generate_nested_boxes,
    generate_simple_nested_boxes,
    generate_test_cross_section,
    generate_assembly,
)


def test_nested_cubes():
    """
    Tests to make sure that the nested cubes do not cause the correct number of surfaces
    in the mesh.
    """

    # Create the basic assembly
    assy = generate_nested_boxes()

    # Convert the assembly to a GMSH mesh
    gmsh = assy.getTaggedGmsh()

    # Make sure we have the correct number of surfaces
    surfaces = gmsh.model.getEntities(2)
    assert len(surfaces) == 18


def test_imprinted_assembly_mesh():
    """
    Tests to make sure that the imprinted assembly mesh works correctly with tagging.
    """

    # Create the basic assembly
    assy = generate_test_cross_section()

    # Convert eh assembly to an imprinted GMSH mesh
    gmsh = assy.getImprintedGmsh()

    # Make sure we have the correct number of surfaces
    surfaces = gmsh.model.getEntities(2)
    assert len(surfaces) == 56


def test_basic_assembly():
    """
    Tests to make sure that the most basic assembly works correctly with tagging.
    """

    # Create the basic assembly
    assy = generate_simple_nested_boxes()

    # Create a mesh that has all the faces tagged as physical groups
    assy.saveToGmsh(mesh_path="tagged_mesh.msh")


def test_basic_cross_section():
    """
    Tests to make sure that tagging works correctly between a simple CadQuery assembly and Gmsh.
    """

    # Create the cross-section assembly
    assy = generate_test_cross_section()

    # Create a mesh that has all the faces in the correct physical groups
    assy.saveToGmsh(mesh_path="tagged_cross_section.msh")


def test_planar_coil():
    """
    Test to make sure a full coil that has a centroid that is planar works with tagging correctly.
    """

    # Create the planar coil assembly
    assy = generate_assembly()

    # Create a mesh that has all the faces in the correct physical groups
    assy.saveToGmsh(mesh_path="tagged_planar_coil.msh")
