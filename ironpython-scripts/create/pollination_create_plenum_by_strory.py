"""
Create new room starting from ceilings or roofs of a model story
------------------------------------------------------------------------------
Instructions:
    1. Run the script
    2. Select the story
    3. Create a new room
------------------------------------------------------------------------------
Strategy:
    1. Get all Pollination Rooms
    2. Get all Pollination Room Story
    3. Use ExtractSrf and ExtrudeSrf
"""
# TODO: Fix undo, fix programType

# import rhinocommon and Eto
import Rhino
import System
import Rhino.UI
import Eto.Drawing as drawing
import Eto.Forms as forms

# import pollination part
import clr
clr.AddReference('Pollination.Core.dll')
clr.AddReference('HoneybeeSchema.dll')
import HoneybeeSchema as hb # csharp version of HB Schema
import Core as po # It contains Pollination RhinoObject classes
import Core.Convert as co # It contains utilities to convert RhinoObject <> HB Schema
from Core.Entity import EntityHelper, ModelEntity 

# import List collection
from System.Collections.Generic import List

try:  # import honeybee dependencies
    import honeybee.dictutil as hb_dict_util
    from honeybee.room import Room
except ImportError as e:
    raise ImportError('\nFailed to import:\n\t{}'.format(e))

# SELECTION PART
#---------------------------------------------------------------------------------------------#
# doc info
doc = Rhino.RhinoDoc.ActiveDoc
tol = doc.ModelAbsoluteTolerance
a_tol = doc.ModelAngleToleranceRadians
current_model = po.Entity.ModelEntityTable.Instance.CurrentModelEntity
doc_unit = Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem

# get all objects
objects = Rhino.RhinoDoc.ActiveDoc.Objects

# filter by rooms
rooms = [_ for _ in objects if isinstance(_, po.Objects.RoomObject)]

if not rooms:
    raise ValueError('No rooms found.')

# define Eto window
class StorySelection(forms.Dialog[str]):
    
    def __init__(self, story):
        self.Title = 'Story Selection - extrude roof/ceilings'
        self.Resizable = True
        self.Width = 300
        self.m_dropdownlist = forms.DropDown()
        self.m_dropdownlist.DataStore = story
        
        self.m_button = forms.Button(Text = 'extrude roof/ceilings')
        self.m_button.Click += self.OnButtonClick
        
        layout = forms.DynamicLayout()
        layout.Padding = drawing.Padding(10)
        layout.Spacing = drawing.Size(5, 5)
        layout.Add(self.m_dropdownlist)
        layout.Add(self.m_button)
        
        self.Content = layout
    
    def OnButtonClick(self, s, e):
        if self.m_dropdownlist.SelectedValue:
            self.Close(self.m_dropdownlist.SelectedValue)

# TRANSFORMATION PART
#---------------------------------------------------------------------------------------------#

story = list(set([_.Data.HBObjectCopy.Story for _ in rooms]))

dialog = StorySelection(story)
rc = dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

properties = []
for rm in rooms:
    if rm.Data.HBObjectCopy.Story == rc:
        for fc in rm.BrepGeometry.Faces:
            fc_data = EntityHelper.TryGetFaceDataCopy(fc)
            hb_obj = fc_data.HBObjectCopy
            index = fc.ComponentIndex()
            
            # select only if roof ceiling
            if hb_obj.FaceType == hb.FaceType.RoofCeiling:
                
                rm.SelectSubObject(index, True, True)

existing_object = doc.Objects
rooms = List[po.Objects.RoomObject]()


# run ExtractSrf and ExtrudeSrf commands
Rhino.RhinoApp.RunScript('ExtractSrf Copy=Yes _Enter', False)
Rhino.RhinoApp.RunScript('ExtrudeSrf Solid=Yes DeleteInput=Yes', False)
for obj in doc.Objects:
    if obj not in existing_object:
        if not isinstance(obj, Rhino.DocObjects.BrepObject):
            continue
        
        brep = Rhino.Geometry.Brep.TryConvertBrep(obj.Geometry)
        if brep:
            room_energy_prop = hb.RoomEnergyPropertiesAbridged(programType="Plenum")
            new_room = po.Objects.RoomObject(brep, tol)
            new_room.Id = obj.Id
            new_room.SetEnergyProp(room_energy_prop)
            
            rooms.Add(new_room)

if rooms:
    ModelEntity.AddHBObjs(doc, rooms)
doc.Views.Redraw()