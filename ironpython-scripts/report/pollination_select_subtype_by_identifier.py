"""
Search sub-objects by Identifier
------------------------------------------------------------------------------
Instructions:
    1. Run the script
    2. Type the keyword
------------------------------------------------------------------------------
Strategy:
    1. Get all Pollination Rooms
    2. Seach by Identifier (Apertures, Doors, Faces)
"""

# import rhinocommon and Eto
import Rhino
import System
import Rhino.UI
import Eto.Drawing as drawing
import Eto.Forms as forms
import re

# import pollination part
import clr
clr.AddReference('Pollination.Core.dll')
clr.AddReference('HoneybeeSchema.dll')
import HoneybeeSchema as hb # csharp version of HB Schema
import Core as po # It contains Pollination RhinoObject classes
import Core.Convert as co # It contains utilities to convert RhinoObject <> HB Schema
from Core import EntityHelper


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
#----------------------------------------------------------------------------#
# doc info
doc = Rhino.RhinoDoc.ActiveDoc
tol = doc.ModelAbsoluteTolerance
a_tol = doc.ModelAngleToleranceRadians
current_model = po.ModelEntityTable.Instance
doc_unit = Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem

# get all objects
objects = Rhino.RhinoDoc.ActiveDoc.Objects

# filter by rooms
rooms = [_ for _ in objects if isinstance(_, po.Objects.RoomObject)]

if not rooms:
    raise ValueError('No rooms found.')

# define Eto window
class KeywordSelection(forms.Dialog[str]):
    
    def __init__(self):
        self.Title = 'Keyword to use (DisplayName)'
        self.Resizable = True
        self.Width = 300
        self.m_textbox = forms.TextBox(Text = 'Keyword here!')
        
        self.m_button = forms.Button(Text = 'Search')
        self.m_button.Click += self.OnButtonClick
        
        layout = forms.DynamicLayout()
        layout.Padding = drawing.Padding(10)
        layout.Spacing = drawing.Size(5, 5)
        layout.Add(self.m_textbox)
        layout.Add(self.m_button)
        
        self.Content = layout
    
    def OnButtonClick(self, s, e):
        if self.m_textbox.Text:
            self.Close(self.m_textbox.Text)

#-----------------------------------------------------------------------------#

def select_childs(childs, 
                  helpher_method, 
                  keyword="",
                  attribute="Identifier"):
    """Search by Attribute"""
    r = re.compile(".*{0}.*".format(keyword))
    for elm in childs:
        data = helpher_method(elm.Geometry())
        if r.match(getattr(data, attribute)):
            ok = doc.Objects.Select(elm)
            print getattr(data, attribute)

def select_faces(room, 
                 keyword="",
                 attribute="Identifier"):
    """Search by Attribute"""
    r = re.compile(".*{0}.*".format(keyword))
    faces = room.BrepGeometry.Faces
    
    for elm in faces:
        data = EntityHelper.TryGetFaceDataCopy(elm)
        if r.match(getattr(data, attribute)):
            hb_obj = data.HBObjectCopy
            index = elm.ComponentIndex()
            status = room.SelectSubObject(index, True, True, True)
            print getattr(data, attribute)

dialog = KeywordSelection()
rc = dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

for rm in rooms:
    doors = rm.Doors
    apertures = rm.Apertures
    if apertures: select_childs(apertures, 
                                EntityHelper.TryGetApertureDataCopy, 
                                keyword=rc)
    if doors: select_childs(doors, 
                            EntityHelper.TryGetDoorDataCopy,
                            keyword=rc)
    
    select_faces(rm, keyword=rc)

doc.Views.Redraw()
