import cadquery as cq


def generate_nested_boxes():
    """
    Generates a simple assembly of two cubes where one is nested inside the other.
    """

    # Cube that is nested completely inside the other one
    inside_cube = cq.Workplane().box(5, 5, 5)

    # Use the inside cube to make a void inside the outside cube
    outside_cube = cq.Workplane().box(10, 10, 10)
    outside_cube = outside_cube.cut(inside_cube)

    # Create the assembly
    assy = cq.Assembly()
    assy.add(
        outside_cube,
        name="outside_cube",
        loc=cq.Location(cq.Vector(0, 0, 0)),
        color=cq.Color("blue"),
    )
    assy.add(
        inside_cube,
        name="inside_cube",
        loc=cq.Location(cq.Vector(0, 0, 0)),
        color=cq.Color("red"),
    )

    return assy


def generate_simple_nested_boxes():
    """
    Generates the simplest assembly case where two boxes are nested inside each other.
    """

    # Create the outter shell
    shell = cq.Workplane("XY").box(50, 50, 50)
    shell = shell.faces(">Z").workplane().rect(21, 21).cutThruAll()
    shell.faces(">X[-2]").tag("inner-right")
    shell.faces("<X[-2]").tag("~in_contact")

    # Create the insert
    insert = cq.Workplane("XY").box(20, 20, 50)
    insert.faces("<X").tag("~in_contact")
    insert.faces(">X").tag("outer-right")

    assy = cq.Assembly()
    assy.add(
        shell, name="shell", loc=cq.Location(cq.Vector(0, 0, 0)), color=cq.Color("red")
    )
    assy.add(
        insert,
        name="insert",
        loc=cq.Location(cq.Vector(0, 0, 0)),
        color=cq.Color("blue"),
    )

    return assy


def generate_test_cross_section():
    """
    Generates a basic cross-section to verify that the tagged faces are crossing over
    between the CadQuery and mesh domains.
    """

    # mat1 1
    mat1_1 = cq.Workplane().rect(4.99, 4.99).extrude(20.0)
    mat1_1.faces(">X").tag("external-right")
    mat1_1.faces("<X").tag("external-left")
    mat1_1.faces(">Y").tag("external-top")
    mat1_1.faces("<Y").tag("external-bottom")

    # mat1 2
    mat1_2 = cq.Workplane().rect(4.99, 4.99).extrude(20.0)
    mat1_2.faces(">X").tag("external-right")
    mat1_2.faces("<X").tag("external-left")
    mat1_2.faces(">Y").tag("external-top")
    mat1_2.faces("<Y").tag("external-bottom")

    # mat2 1
    mat2_1 = cq.Workplane().rect(9.9, 9.9).rect(5.0, 5.0).extrude(20.0)
    mat2_1 = mat2_1.faces(">Z").rect(5.0, 5.0).cutThruAll()
    mat2_1.faces(">Y[-2]").tag("internal-top")
    mat2_1.faces("<Y[-2]").tag("internal-bottom")
    mat2_1.faces("<X[-2]").tag("internal-left")
    mat2_1.faces(">X[-2]").tag("internal-right")
    mat2_1.faces(">X").tag("external-right")
    mat2_1.faces("<X").tag("external-left")
    mat2_1.faces("<Y").tag("external-bottom")
    mat2_1.faces(">Y").tag("~contact_with_mat4")

    # mat2 2
    mat2_2 = cq.Workplane().rect(9.9, 9.9).rect(5.0, 5.0).extrude(20.0)
    mat2_2 = mat2_2.faces(">Z").rect(5.0, 5.0).cutThruAll()
    mat2_2.faces(">Y[-2]").tag("internal-top")
    mat2_2.faces("<Y[-2]").tag("internal-bottom")
    mat2_2.faces("<X[-2]").tag("internal-left")
    mat2_2.faces(">X[-2]").tag("internal-right")
    mat2_2.faces(">X").tag("external-right")
    mat2_2.faces("<X").tag("external-left")
    mat2_2.faces("<Y").tag("external-bottom")
    mat2_2.faces(">Y").tag("~contact_with_mat4")

    # mat3 3
    mat3_3 = cq.Workplane().move(0.0, -1.0).rect(40.0, 12.0).extrude(20.0)
    mat3_3 = (
        mat3_3.faces(">Y")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(10.0, 0.0), (-10.0, 0.0)])
        .rect(10.0, 20.0)
        .cutBlind(-10.0)
    )
    mat3_3.faces(">X[-2]").tag("internal-right")
    mat3_3.faces(">X[-3]").tag("internal-middle-right")
    mat3_3.faces(">X[-4]").tag("internal-middle-left")
    mat3_3.faces(">X[-5]").tag("internal-left")
    mat3_3.faces("<Y[-2]").tag("internal-bottom")
    mat3_3.faces(">X or >Y or <X or <Y").tag("~contact_with_mat4")

    # mat4
    mat4 = cq.Workplane().rect(50.0, 50.0).extrude(20.0)
    mat4 = (
        mat4.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .move(0.0, -1.0)
        .rect(40.1, 12.1)
        .cutThruAll()
    )
    mat4.faces(">X[-2]").tag("internal-right")
    mat4.faces("<X[-2]").tag("internal-left")
    mat4.faces("<Y[-2]").tag("internal-bottom")
    mat4.faces(">Y[-2]").tag("internal-top")

    assy = cq.Assembly()
    assy.add(
        mat1_1,
        name="mat1_1",
        color=cq.Color("yellow"),
        loc=cq.Location(cq.Vector(10.0, 0, 0)),
    )
    assy.add(
        mat1_2,
        name="mat1_2",
        color=cq.Color("yellow"),
        loc=cq.Location(cq.Vector(-10.0, 0, 0)),
    )
    assy.add(
        mat2_1,
        name="mat2_1",
        color=cq.Color("green"),
        loc=cq.Location(cq.Vector(10.0, 0, 0)),
    )
    assy.add(
        mat2_2,
        name="mat2_2",
        color=cq.Color("green"),
        loc=cq.Location(cq.Vector(-10.0, 0, 0)),
    )
    assy.add(mat3_3, name="mat3_3", color=cq.Color("blue"))
    assy.add(mat4, name="mat4", color=cq.Color("gray"))

    return assy


def generate_assembly():
    """
    Generates a simple assembly for testing.
    """

    # parameters
    radius = 1000
    mat1_side_length = 4
    mat2_side_length = 15
    mat3_width = 50
    mat3_height = 20
    mat4_length = 100

    centroid = cq.Workplane().circle(radius)

    # mat4
    mat4_section = (
        cq.Workplane("XZ")
        .center(x=radius, y=0)
        .rect(xLen=mat4_length, yLen=mat4_length)
    )
    mat4_body = mat4_section.sweep(path=centroid)

    # plate
    mat3_section = (
        cq.Workplane("XZ")
        .center(x=radius, y=-(mat3_height - mat2_side_length) / 2)
        .rect(xLen=mat3_width, yLen=mat3_height)
    )
    mat3_body = mat3_section.sweep(path=centroid)
    mat4_body = mat4_body.cut(mat3_body)

    # mat2
    mat2_section = (
        cq.Workplane("XZ")
        .center(x=radius - mat3_width / 4, y=0)
        .rect(xLen=mat2_side_length, yLen=mat2_side_length)
    )
    mat2_section.center(x=mat3_width / 2, y=0).rect(
        xLen=mat2_side_length, yLen=mat2_side_length
    )
    mat2_body = mat2_section.sweep(centroid)
    mat3_body = mat3_body.cut(mat2_body)

    # mat1
    mat1_section = (
        cq.Workplane("XZ")
        .center(x=radius - mat3_width / 4, y=0)
        .rect(xLen=mat1_side_length, yLen=mat1_side_length)
    )
    mat1_section.center(x=mat3_width / 2, y=0).rect(
        xLen=mat1_side_length, yLen=mat1_side_length
    )
    mat1_body = mat1_section.sweep(centroid)
    mat2_body = mat2_body.cut(mat1_body)

    # Tag the mat1 faces
    (
        mat1_body.faces(cq.selectors.TypeSelector("CYLINDER"))
        .faces(cq.selectors.AreaNthSelector(0))
        .tag("external-inside")
    )
    (
        mat1_body.faces(cq.selectors.TypeSelector("CYLINDER"))
        .faces(cq.selectors.AreaNthSelector(1))
        .tag("external-2nd-inside")
    )
    (
        mat1_body.faces(cq.selectors.TypeSelector("CYLINDER"))
        .faces(cq.selectors.AreaNthSelector(2))
        .tag("external-2nd-outside")
    )
    (
        mat1_body.faces(cq.selectors.TypeSelector("CYLINDER"))
        .faces(cq.selectors.AreaNthSelector(3))
        .tag("external-outside")
    )
    mat1_body.faces(">Z").tag("external-top")
    mat1_body.faces("<Z").tag("external-bottom")

    # Tag the mat2 faces
    (mat2_body.faces("<Z").tag("external-bottom"))
    (
        mat2_body.faces(cq.selectors.TypeSelector("CYLINDER"))
        .faces(cq.selectors.AreaNthSelector(0))
        .tag("inside")
    )

    # assembly
    assembly = cq.Assembly()
    assembly.add(mat1_body, name="mat1", color=cq.Color("yellow"))
    # assembly.add(mat2_body, name="mat2", color=cq.Color("green"))
    assembly.add(mat3_body, name="mat3", color=cq.Color("blue"))
    assembly.add(mat4_body, name="mat4", color=cq.Color("gray"))

    return assembly


def generate_subshape_assembly():
    """
    Generates a simple assembly with subshapes for testing.
    """

    # Create a simple assembly
    assy = cq.Assembly(name="top-level")
    cube_1 = cq.Workplane().box(10.0, 10.0, 10.0)
    assy.add(cube_1, name="cube_1", color=cq.Color("green"))

    # Add subshape name, color and layer
    assy.addSubshape(
        cube_1.faces(">Z").val(),
        name="cube_1_top_face",
        color=cq.Color("red"),
        layer="cube_1_top_face",
    )

    return assy
