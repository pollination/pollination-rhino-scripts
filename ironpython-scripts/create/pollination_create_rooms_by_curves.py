"""
Create rooms from closed curves.
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
clr.AddReference('Honeybee.UI.Rhino.dll')
import HoneybeeSchema as hb # csharp version of HB Schema
import Core as sh # It contains Pollination RhinoObject classes
import Core.Convert as co # It contains utilities to convert RhinoObject <> HB Schema
import Honeybee.UI as hu
from System.Collections.Generic import List

# Pollination Rhino Plugin is inside rhp
id = Rhino.PlugIns.PlugIn.IdFromName("Pollination.RH")
PollinationRhinoPlugIn = Rhino.PlugIns.PlugIn.Find(id)

# SELECTION PART
#---------------------------------------------------------------------------------------------#
# doc info
doc = Rhino.RhinoDoc.ActiveDoc
tol = doc.ModelAbsoluteTolerance
a_tol = doc.ModelAngleToleranceRadians
current_model = sh.Entity.ModelEntityTable.Instance.CurrentModelEntity
doc_unit = Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem

default_height = {
    Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem.Meters: 3,
    Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem.Centimeters: 300,
    Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem.Millimeters: 3000,
    Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem.Feet: 9.84,
    Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem.Inches: 118
}

if not default_height.has_key(doc_unit):
    raise ValueError('Unit not supported.')

# define Eto grid
class RoomGridView(forms.Dialog[list]):
    
    def __init__(self, data):
        unit = str(doc_unit).lower()
        
        self._data_dict = {}
        self._data = data
        self.Title = "Closed curve - Room generator"
        self.Resizable = True
        self.m_gridview = forms.GridView()
        self.m_gridview.ShowHeader = True
        self.m_gridview.DataStore = data
        self.m_gridview.Height = 300
        self.m_gridview.Width = 300 
        self.m_gridview.CellDoubleClick += self.OnDoubleClickLayer
        
        self._header = ('LayerName', 'Height ({})'.format(unit), 'Export')
        
        column1 = forms.GridColumn()
        column1.HeaderText = self._header[0]
        column1.DataCell = forms.TextBoxCell(0)
        column1.Width = 195
        self.m_gridview.Columns.Add(column1)

        column2 = forms.GridColumn()
        column2.HeaderText = self._header[1]
        column2.Editable = True
        column2.DataCell = forms.TextBoxCell(1)
        column2.Width = 95
        self.m_gridview.Columns.Add(column2)
        
        self.m_button = forms.Button(self.OnClickButton)
        self.m_button.Text = 'Run It!'
        
        layout = forms.DynamicLayout()
        layout.Padding = drawing.Padding(10)
        layout.Spacing = drawing.Size(5, 5)
        layout.Add(forms.Label(Text = '1. Double click on a row to set room properties.'))
        layout.Add(forms.Label(Text = '2. One click on the height cell tso edit the room height.'))
        layout.Add(self.m_gridview)
        layout.Add(self.m_button)
        layout.Add(forms.Label(Text = 'Only planar closed curves are supported.'))
        self.Content = layout
    
    def OnClickButton(self, s, e):
        out_data = []
        
        for i, data in enumerate(self._data):
            name, height, cecked, geometries = data
            if geometries and self._data_dict.has_key(i):
                out_data.append([name, height, cecked, geometries, self._data_dict[i]])
        
        self.Close(out_data)
    
    def OnDoubleClickLayer(self, s, e):
        # Properties of the Model
        properties = current_model.HBModelProperties.DuplicateModelProperties()
        room_prop = hb.RoomPropertiesAbridged()
        dummy_room = hb.Room("empty", List[hb.Face](), room_prop)
        
        # create a List of rooms
        rooms = List[hb.Room]()
        rooms.Add(dummy_room)
        
        dialog = hu.Dialog_RoomProperty(properties, rooms)
        dialog_rc = dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
        
        if dialog_rc:
            room = dialog_rc[0]
            energy = room.Properties.Energy
            self._data_dict[e.Row] = energy
            current_model.SetModelProperty(properties)

def select_objects(layer_table_names):
    objects = []
    for layer in layer_table_names:
        sub_objects = []
        for obj in Rhino.RhinoDoc.ActiveDoc.Objects:
            if layer_table_names[obj.Attributes.LayerIndex] == layer:
                # planar closed curve only
                geometry = obj.Geometry
                if isinstance(geometry, Rhino.Geometry.Curve) \
                and geometry.IsClosed and geometry.IsPlanar:
                    sub_objects.append(geometry)
        objects.append(sub_objects)
    return objects

def create_solid(crv, height):
    srf = Rhino.Geometry.Extrusion.CreateExtrusion(crv, Rhino.Geometry.Vector3d(0, 0, float(height))).ToBrep()
    brep = srf.CapPlanarHoles(tol)
    return brep

# Get dataset
layer_table = [_ for _ in Rhino.RhinoDoc.ActiveDoc.Layers if (not _.IsLocked and _.IsValid)]
layer_table_names = map(str, layer_table)
heights = [default_height[doc_unit]] * len(layer_table_names)
checked = [False] * len(layer_table_names)

# prepare geometries
geometries = select_objects(layer_table_names)

data = [[n, h, c, g] for n, h, c, g in zip(layer_table_names, heights, checked, geometries)]

# run eto
dialog = RoomGridView(data)
rc = dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

if rc:
    # create pollination rooms
    for dt in rc:
        name, height, checked, geometries, properties = dt
        
        # create a List of rooms
        rooms = List[sh.Objects.RoomObject]()
        
        for geo in geometries:
            geo = create_solid(geo, height)
            if (geo is None or not geo.IsValid or not geo.IsSolid): continue
            test = doc.Objects.AddBrep(geo)
            brep_object = doc.Objects.Find(test)
            
            if brep_object:
                brep = Rhino.Geometry.Brep.TryConvertBrep(brep_object.Geometry)
                new_room = sh.Objects.RoomObject(brep, tol)
                new_room.SetEnergyProp(properties)
                
                # Add rooms
                new_room.Id = brep_object.Id
                rooms.Add(new_room)
        
        if rooms:
            PollinationRhinoPlugIn.AddHBObjs(doc, rooms)
doc.Views.Redraw()