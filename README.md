![Project Logo](docs/images/logo.png)

CadQuery plugin to create a mesh of an assembly with corresponding data.

This plugin makes use of CadQuery tags to collect surfaces into [Gmsh](https://gmsh.info/) physical groups. The
tagged faces are matched to their corresponding surfaces in the mesh via their position in the CadQuery solid(s) vs the Gmsh surface ID. There are a few challenges with mapping tags to surfaces to be aware of.

1. Each tag can select multiple faces/surfaces at once, and this has to be accounted for when mapping tags to surfaces.
2. Tags are present at the higher level of the Workplane class, but are do not propagate to lower-level classes like Face.
3. OpenCASCADE does not provide a built-in mechanism for tagging low-level entities without the use of an external data structure or framework.

## Installation

You can install via [PyPI](https://pypi.org/project/assembly-mesh-plugin/)

```
pip install assembly-mesh-plugin
```

## Usage

**PLEASE NOTE:** This plugin currently needs to be run in an Anaconda/Mamba environment because of a crash with the PyPI packages when passing OpenCASCADE objects to Gmesh in memory.

The plugin needs to be imported in order to monkey-patch its method into CadQuery:

```python
import assembly_mesh_plugin
```

You can then tag faces in each of the assembly parts and create your assembly. To export the assembly to a mesh file, you do the following.

```python
your_assembly.saveToGmsh(mesh_path="tagged_mesh.msh")
```

Normal tag names lead to a physical group with the assembly part name prefixed. So a tag name of `inner-bottom` on an assembly part with the name `steel_plate` will be `steel_plate_inner-bottom`

By prefixing a tag with the `~` character, the part name is ignored, which allows for tagging of a multi-material
physical group. For instance, tagging multiple faces with `~contact-with-casing` will produce a physical group with the name `contact-with-casing` that includes all those faces, even if they belong to different parts/solids.

Below is a simple example.

```python
import cadquery as cq
import assembly_mesh_plugin

shell = cq.Workplane("XY").box(50, 50, 50)
shell = shell.faces(">Z").workplane().rect(21, 21).cutThruAll()
shell.faces(">X[-2]").tag("inner-right")
shell.faces("<X[-2]").tag("~in_contact")

# Create the insert
insert = cq.Workplane("XY").box(20, 20, 50)
insert.faces("<X").tag("~in_contact")
insert.faces(">X").tag("outer-right")

assy = cq.Assembly()
assy.add(shell, name="shell")
assy.add(insert, name="insert")

assy.saveToGmsh(mesh_path="tagged_mesh.msh")
```

The resulting `.msh` file should have three physical groups named for tags in it. The `in_contact` group should include the faces from both the shell and the insert.

If you want more control over the mesh generation and export, you can use the `getTaggedGmsh` method and then finalize the mesh yourself.

```python
import cadquery as cq
import assembly_mesh_plugin
import gmsh

shell = cq.Workplane("XY").box(50, 50, 50)
shell = shell.faces(">Z").workplane().rect(21, 21).cutThruAll()
shell.faces(">X[-2]").tag("inner-right")
shell.faces("<X[-2]").tag("~in_contact")

# Create the insert
insert = cq.Workplane("XY").box(20, 20, 50)
insert.faces("<X").tag("~in_contact")
insert.faces(">X").tag("outer-right")

assy = cq.Assembly()
assy.add(shell, name="shell")
assy.add(insert, name="insert")

# Get a Gmsh object back with all the tagged faces as physical groups
gmsh_object = assy.getTaggedGmsh()

# Generate the mesh and write it to the file
gmsh_object.model.mesh.field.setAsBackgroundMesh(2)
gmsh_object.model.mesh.generate(3)
gmsh_object.write("tagged_mesh.msh")
gmsh_object.finalize()
```

## Tests

These tests are also run in Github Actions, and the meshes which are generated can be viewed as artifacts on the successful `tests` Actions there.

* [sample_coils.py](tests/sample_coils.py) contains generators for sample assemblies for use in testing the basic operation of this plugin. This file also contains the code to tag all faces of interest.
* [smoke_test.py](tests/smoke_test.py) runs two tests currently. The first is for a simple cross-section of a coil (image below), which makes it easier to verify basic operation. The second is for a planar coil, which forces the use of more advanced selectors, but is not as complex as a coil with a non-planar sweep path. This planar-coil test is not complete yet.

Once the test has been run (using the pytest command), two mesh files (.msh extension) be created in the root of the repository.

* tagged_cross_section.msh
* tagged_planar_coil.msh

These mesh files will have many physical groups since each surface gets its own physical group, but it should also contain physical groups corresponding to the tags that were created for the faces in the assembly parts.
