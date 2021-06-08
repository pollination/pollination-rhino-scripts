"""
Create a simple report on runtime to check rooms
------------------------------------------------------------------------------
Instructions:
    1. Run the script
------------------------------------------------------------------------------
Strategy:
    1. Get all Pollination Rooms
    2. Use Honeybee for reporting
"""

# import rhinocommon and Eto
import Rhino
import System
import Rhino.UI
import Eto.Drawing as drawing
import Eto.Forms as forms

# import pollination part
import clr
clr.AddReference('Share.dll')
clr.AddReference('HoneybeeSchema.dll')
import HoneybeeSchema as HB # csharp version of HB Schema
import Share as SH # It contains Pollination RhinoObject classes
import Share.Convert as CO # It contains utilities to convert RhinoObject <> HB Schema

# import List collection
from System.Collections.Generic import List

try:  # import honeybee dependencies
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
current_model = SH.Entity.ModelEntityTable.Instance.CurrentModelEntity
doc_unit = Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem

# get all objects
objects = Rhino.RhinoDoc.ActiveDoc.Objects

# filter by rooms
rooms = [_ for _ in objects if isinstance(_, SH.Objects.RoomObject)]

if not rooms:
    raise ValueError('No rooms found.')

# REPORTING PART
#---------------------------------------------------------------------------------------------#

# define Eto grid
class RoomGridView(forms.Dialog[bool]):
    
    def __init__(self, data):
        unit = str(doc_unit).lower()
        
        self.Title = "Room report"
        self.Resizable = True
        self.m_gridview = forms.GridView()
        self.m_gridview.ShowHeader = True
        
        self.m_gridview.DataStore = data

        column1 = forms.GridColumn()
        column1.HeaderText = 'display_name'
        column1.Editable = True
        column1.DataCell = forms.TextBoxCell(0)
        self.m_gridview.Columns.Add(column1)

        column2 = forms.GridColumn()
        column2.HeaderText = 'floor_area [{}2]'.format(unit)
        column2.Editable = True
        column2.DataCell = forms.TextBoxCell(1)
        self.m_gridview.Columns.Add(column2)

        column3 = forms.GridColumn()
        column3.HeaderText = 'volume [{}3]'.format(unit)
        column3.Editable = True
        column3.DataCell = forms.TextBoxCell(2)
        self.m_gridview.Columns.Add(column3)

        column4 = forms.GridColumn()
        column4.HeaderText = 'exposed_area [{}2]'.format(unit)
        column4.Editable = True
        column4.DataCell = forms.TextBoxCell(3)
        self.m_gridview.Columns.Add(column4)
        
        column5 = forms.GridColumn()
        column5.HeaderText = 'exterior_wall_aperture_area [{}2]'.format(unit)
        column5.Editable = True
        column5.DataCell = forms.TextBoxCell(4)
        self.m_gridview.Columns.Add(column5)
        
        column6 = forms.GridColumn()
        column6.HeaderText = 'exterior_wall_area [{}2]'.format(unit)
        column6.Editable = True
        column6.DataCell = forms.TextBoxCell(5)
        self.m_gridview.Columns.Add(column6)
        
        layout = forms.DynamicLayout()
        layout.Padding = drawing.Padding(10)
        layout.Spacing = drawing.Size(5, 5)
        layout.Add(self.m_gridview)
        
        self.Content = layout

# create the dataset
data = []
for rm in rooms:
    hb_dict = json.loads(rm.ToHBObject().ToJson())
    hb_room = hb_dict_util.dict_to_object(hb_dict, False)
    numeric = [hb_room.floor_area, \
                hb_room.volume, hb_room.exposed_area, hb_room.exterior_wall_aperture_area, \
                hb_room.exterior_wall_area]
    numeric = map(int, numeric)
    
    row = [hb_room.display_name]
    row.extend(numeric)
    
    data.append(row)

# show the table
if rooms:
    dialog = RoomGridView(data)
    rc = dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)