"""
Move face of all ceiling or roof of a model story
------------------------------------------------------------------------------
Instructions:
    1. Run the script
    2. Select the story
    3. Move it
------------------------------------------------------------------------------
Strategy:
    1. Get all Pollination Rooms
    2. Get all Pollination Room Story
    3. Use RhinoApp MoveFace
"""

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
from Core.Entity import EntityHelper

# import List collection
from System.Collections.Generic import List

try:  # import honeybee dependencies
    import io
    import csv
    import json
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
        self.Title = 'Story Selection - move roof/ceilings'
        self.Resizable = True
        self.Width = 300
        self.m_dropdownlist = forms.DropDown()
        self.m_dropdownlist.DataStore = story
        
        self.m_button = forms.Button(Text = 'Move roof/ceilings')
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

for rm in rooms:
    if rm.Data.HBObjectCopy.Story == rc:
        for fc in rm.BrepGeometry.Faces:
            fc_data = EntityHelper.TryGetFaceDataCopy(fc)
            hb_obj = fc_data.HBObjectCopy
            index = fc.ComponentIndex()
            
            # select only if roof ceiling
            if hb_obj.FaceType == hb.FaceType.RoofCeiling:
                rm.SelectSubObject(index, True, True)

# run moveface command using the automatic selection
Rhino.RhinoApp.RunScript('MoveFace', False)
doc.Objects.UnselectAll()
doc.Views.Redraw()