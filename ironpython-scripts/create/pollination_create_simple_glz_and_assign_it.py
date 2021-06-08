"""
Create a simple glz construction and add it to apertures of the selected rooms
------------------------------------------------------------------------------
Instructions:
    1. Change the material properties
    2. Run the script
------------------------------------------------------------------------------
Strategy:
    1. Create a window construction first
    2. Construction assignment - Pollination rooms > Apertures > Set aperture construction
"""

# import rhinocommon
import Rhino

# import pollination part
import clr
clr.AddReference('Share.dll')
clr.AddReference('HoneybeeSchema.dll')
import HoneybeeSchema as HB # csharp version of HB Schema
import Share as SH # It contains Pollination RhinoObject classes
import Share.Convert as CO # It contains utilities to convert RhinoObject <> HB Schema

# import List collection
from System.Collections.Generic import List

# USER PARAMETERS
# --------------------------------------------------------------------------------------------#
# custom window simple glass ID, U, SHGC, DisplayName, VLT
simple_glass = HB.EnergyWindowMaterialSimpleGlazSys("my_glass_0_75", 1.5, 0.75, "my_glass_0_75", 0.8)
# --------------------------------------------------------------------------------------------#

# SELECTION PART
#---------------------------------------------------------------------------------------------#
# doc info
doc = Rhino.RhinoDoc.ActiveDoc
tol = doc.ModelAbsoluteTolerance
a_tol = doc.ModelAngleToleranceRadians
current_model = SH.Entity.ModelEntityTable.Instance.CurrentModelEntity

# start the command
go = Rhino.Input.Custom.GetObject()

# set the selection
go.SetCommandPrompt('Please, select pollination rooms')
go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
go.GroupSelect = False
go.SubObjectSelect = False
go.AcceptNothing(True)
go.GetMultiple(0, 0)

# filter by rooms
rooms = [_.Object() for _ in go.Objects() if isinstance(_.Object(), SH.Objects.RoomObject)]

if not rooms:
    raise ValueError('Please, select pollination rooms')

# TRANSFORMATION PART
#---------------------------------------------------------------------------------------------#
# Properties of the Model
properties = current_model.HBModelProperties

# get all material identifiers
identifiers = [mat.Obj.Identifier for mat in properties.Energy.Materials]

# add window material to the model library
if simple_glass.Identifier not in identifiers:
    print '{} to Library'.format(simple_glass.DisplayName)
    HB.Extension.AddMaterial(properties.Energy, simple_glass)

# custom window construction
glass_construction_materials = List[str]()
glass_construction_materials.Add(simple_glass.Identifier)

# create window construction
window_construction = HB.WindowConstructionAbridged("my_simple_window_construction_abridged", glass_construction_materials, "my_simple_window_construction")

# get all construction identifiers
identifiers = [mat.Obj.Identifier for mat in properties.Energy.Constructions]

# add window abridged construction to the model library
if window_construction.Identifier not in identifiers:
    print '{} to Library'.format(window_construction.DisplayName)
    HB.Extension.AddConstruction(properties.Energy, window_construction)

# apply my custom window abridged construcition to apertures of the selected rooms
for rm in rooms:
    for apt in rm.Apertures:
        obj = apt.Object()
        apt_copy = obj.DuplicateApertureObject()
        apt_copy.SetConstruction(window_construction.Identifier)
        doc.Objects.Replace(Rhino.DocObjects.ObjRef(obj.Id), apt_copy)
