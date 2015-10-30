# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CalculateRegion
								 A QGIS plugin
 This tool is used to calculate area in tile shapefiles
								-------------------
		begin                : 2015-10-08
		git sha              : $Format:%H$
		copyright            : (C) 2015 by Bernard Silva - LAPIG/UFG
		email                : so_geoprocessamento@yahoo.com.br
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication,QThread, QObject, pyqtSignal
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QProgressBar, QMessageBox
import PyQt4.QtGui

# Initialize Qt resources from file resources.py
import resources

# Import the code for the dialog
from CalculateRegion_dialog import CalculateRegionDialog

# Auxiliary modules
import os.path
import ogr, glob
import qgis.utils


class Worker(QObject):
		'''Example worker for calculating the total area of all features in a layer'''
		
		def __init__(self, ExtrairShape, CalcShape, OutShape, TypeUnits):
				QObject.__init__(self)
				self.killed = False
				self.ExtrairShape = ExtrairShape
				
				self.CalcShape = CalcShape
				self.OutShape = OutShape
				self.TypeUnits = TypeUnits
				

		def run(self):
				listShapes = glob.glob(os.path.join(self.ExtrairShape,'*.shp'))
				drv = ogr.GetDriverByName('ESRI ShapeFile')
				
				#Generate output file
				shapeIn = drv.Open(self.CalcShape,0)
				Layers = shapeIn.GetLayer(0)
				tGeom = Layers.GetSpatialRef()
				vGeom = tGeom.IsProjected()
				geom_type = Layers.GetLayerDefn().GetGeomType()
				NameOut = str(os.path.basename(self.OutShape)[0:len(os.path.basename(self.OutShape))-4])
				cds = drv.CreateDataSource(os.path.dirname(self.OutShape))
				cShape =  cds.CreateLayer(NameOut,geom_type = geom_type, srs = tGeom)
				cIns = Layers.GetFeatureCount()
				[cShape.CreateField(Layers.GetFeature(0).GetFieldDefnRef(i)) for i in range(Layers.GetFeature(0).GetFieldCount())]
								
				for geom in range(cIns):
					feat = Layers.GetFeature(geom)
					fDefn = cShape.GetLayerDefn()
					outFeat = ogr.Feature(fDefn)
					outFeat.SetGeometry(feat.GetGeometryRef())
					cShape.CreateFeature(outFeat)
					outFeat.Destroy()
					
				cds.Destroy()
				cShape = None
				
				OpenShape = drv.Open(self.OutShape,1)
				layer = OpenShape.GetLayer(0)		
				countRows = layer.GetFeatureCount()
				for b in range(countRows):
						feat = layer.GetFeature(b)
						for k in range(Layers.GetFeature(b).GetFieldCount()):
									feat.SetField(Layers.GetFeature(b).GetFieldDefnRef(k).name,Layers.GetFeature(b).GetField(k))
									layer.SetFeature(feat)	
				ListFieldName = []
				
				#Add Fields
				for m in listShapes:
					FieldName = str(os.path.basename(m)[len(os.path.basename(m))-13:len(os.path.basename(m))-4])
					field = ogr.FieldDefn(FieldName,ogr.OFTReal)
					field.SetWidth(20)    
					field.SetPrecision(6)
					layer.CreateField(field)
					ListFieldName.append(FieldName)
					FieldName = None
								
				#Calculating Area
				for i in range(countRows):
					for (k,m) in zip(listShapes,range(len(listShapes))):
						AreaDes = 0.00
						gLayer = layer.GetFeature(i)
						geom1 = gLayer.GetGeometryRef()
						X1,X2,Y1,Y2 = geom1.GetEnvelope()
						oDes = drv.Open(k,0)
						olayer = oDes.GetLayer(0)
						olayer.SetSpatialFilterRect(X1,Y1,X2,Y2)
						geom1 = gLayer.GetGeometryRef()
						feat2 = olayer.GetNextFeature()
						while feat2:
							geom2 = feat2.GetGeometryRef()
							if geom2.Intersects(geom1):
								if not geom2.Crosses(geom1):
									clip = geom2.Intersection(geom1)						 
								else:
									clip = geom2
								Area = self.TypeGeom(vGeom,clip.GetArea())
								AreaDes += self.CalcArea(self.TypeUnits,Area)
							feat2.Destroy()
							feat2 = olayer.GetNextFeature()
						gLayer.SetField(ListFieldName[m],AreaDes)
						layer.SetFeature(gLayer)
						oDes.Destroy()
					perc = int(100.00*(float(i)/float(countRows-1)))
					self.progress.emit(perc)
				ListFieldName = None	
				
				self.finished.emit()
		
		def kill(self):
				self.killed = True
		
		def CalcArea(self,Type,Value):
				if Type == 'Hectares':
					return Value/10000.00
				elif Type == 'Square meters':
					return Value
				elif Type == 'Square kilometers': 
					return Value/1000000.00		

		def TypeGeom(self,ValueGeom,ValueArea):
			if ValueGeom == 0:
				return ValueArea * 12100000000.00
			elif ValueGeom == 1:
				return ValueArea			

		finished = pyqtSignal()
		error = pyqtSignal(Exception, basestring)
		progress = pyqtSignal(int)
		
class CalculateRegion:
	"""QGIS Plugin Implementation."""

	def __init__(self, iface):
		"""Constructor.

		:param iface: An interface instance that will be passed to this class
			which provides the hook by which you can manipulate the QGIS
			application at run time.
		:type iface: QgsInterface
		"""
		# Save reference to the QGIS interface
		self.iface = iface
		# initialize plugin directory
		self.plugin_dir = os.path.dirname(__file__)
		# initialize locale
		locale = QSettings().value('locale/userLocale')[0:2]
		locale_path = os.path.join(
			self.plugin_dir,
			'i18n',
			'CalculateRegion_{}.qm'.format(locale))

		if os.path.exists(locale_path):
			self.translator = QTranslator()
			self.translator.load(locale_path)

			if qVersion() > '4.3.3':
				QCoreApplication.installTranslator(self.translator)

		# Create the dialog (after translation) and keep reference
		self.dlg = CalculateRegionDialog()

		# Declare instance attributes
		self.actions = []
		self.menu = self.tr(u'&LAPIG Tools')
		# TODO: We are going to let the user set this up in a future iteration
		self.toolbar = self.iface.addToolBar(u'LAPIG Tools')
		self.toolbar.setObjectName(u'LAPIG Tools')
		self.dlg.pushButtonShape.clicked.connect(self.InputShape)
		self.dlg.pushButtonFolder.clicked.connect(self.InputFolder)
		self.dlg.pushButtonShapeOut.clicked.connect(self.OutputShape)
		self.dlg.lineEditShapeClip.clear()
		self.dlg.lineEditFolder.clear()
		self.dlg.lineEditShapeOut.clear()
		self.ListUnits = ['Square meters','Square kilometers','Hectares']
		self.dlg.Units.addItems(self.ListUnits)

	# noinspection PyMethodMayBeStatic
	def tr(self, message):
		"""Get the translation for a string using Qt translation API.

		We implement this ourselves since we do not inherit QObject.

		:param message: String for translation.
		:type message: str, QString

		:returns: Translated version of message.
		:rtype: QString
		"""
		# noinspection PyTypeChecker,PyArgumentList,PyCallByClass
		return QCoreApplication.translate('CalculateRegion', message)

	def add_action(
		self,
		icon_path,
		text,
		callback,
		enabled_flag=True,
		add_to_menu=True,
		add_to_toolbar=True,
		status_tip=None,
		whats_this=None,
		parent=None):
		"""Add a toolbar icon to the toolbar.

		:param icon_path: Path to the icon for this action. Can be a resource
			path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
		:type icon_path: str

		:param text: Text that should be shown in menu items for this action.
		:type text: str

		:param callback: Function to be called when the action is triggered.
		:type callback: function

		:param enabled_flag: A flag indicating if the action should be enabled
			by default. Defaults to True.
		:type enabled_flag: bool

		:param add_to_menu: Flag indicating whether the action should also
			be added to the menu. Defaults to True.
		:type add_to_menu: bool

		:param add_to_toolbar: Flag indicating whether the action should also
			be added to the toolbar. Defaults to True.
		:type add_to_toolbar: bool

		:param status_tip: Optional text to show in a popup when mouse pointer
			hovers over the action.
		:type status_tip: str

		:param parent: Parent widget for the new action. Defaults None.
		:type parent: QWidget

		:param whats_this: Optional text to show in the status bar when the
			mouse pointer hovers over the action.

		:returns: The action that was created. Note that the action is also
			added to self.actions list.
		:rtype: QAction
		"""

		icon = QIcon(icon_path)
		action = QAction(icon, text, parent)
		action.triggered.connect(callback)
		action.setEnabled(enabled_flag)

		if status_tip is not None:
			action.setStatusTip(status_tip)

		if whats_this is not None:
			action.setWhatsThis(whats_this)

		if add_to_toolbar:
			self.toolbar.addAction(action)

		if add_to_menu:
			self.iface.addPluginToMenu(
				self.menu,
				action)

		self.actions.append(action)

		return action

	def initGui(self):
		"""Create the menu entries and toolbar icons inside the QGIS GUI."""

		icon_path = ':/plugins/CalculateRegion/icon.png'
		self.add_action(
			icon_path,
			text=self.tr(u'Calculate Area in Region'),
			callback=self.run,
			parent=self.iface.mainWindow())

	def unload(self):
		"""Removes the plugin menu item and icon from QGIS GUI."""
		for action in self.actions:
			self.iface.removePluginVectorMenu(
				self.tr(u'&CalculateRegion'),
				action)
			self.iface.removeToolBarIcon(action)
		# remove the toolbar
		del self.toolbar
	
	def run(self):
		
		"""Run method that performs all the real work"""
		# show the dialog
		self.dlg.show()
		# Run the dialog event loop
		result = self.dlg.exec_()
		# See if OK was pressed
		
		Lista = ['Square meters','Square kilometers','Hectares']
		TypeUnits =  Lista[self.dlg.Units.currentIndex()]
	
		if result:
			ExtrairShape = self.dlg.lineEditFolder.text()
			CalcShape = self.dlg.lineEditShapeClip.text()
			OutShape = self.dlg.lineEditShapeOut.text()
			
			self.startWorker(ExtrairShape, CalcShape, OutShape, TypeUnits)
	
	#Function input clip shape file		
	def InputShape(self):
			filters = "ShapeFiles (*.shp)"
			iShape = QFileDialog.getOpenFileName(self.dlg,'Insert Shapefile','',filters)
			self.dlg.lineEditShapeClip.setText(iShape)
	
	#Function input folder shapes
	def InputFolder(self):        
			iFolder = QFileDialog.getExistingDirectory(self.dlg,'Insert Folder','',QFileDialog.ShowDirsOnly)
			self.dlg.lineEditFolder.setText(iFolder)

	#Function output shape file		
	def OutputShape(self):        
			filters = "ShapeFiles (*.shp)"
			oShape = QFileDialog.getSaveFileName(self.dlg,'Output Shapefile','',filters)
			self.dlg.lineEditShapeOut.setText(oShape)

	#Function Start thread processing
	def startWorker(self, ExtrairShape, CalcShape, OutShape, TypeUnits):
			
			# create a new worker instance
			worker = Worker(ExtrairShape, CalcShape, OutShape, TypeUnits)

			# configure the QgsMessageBar
			qgis.utils.iface.messageBar().clearWidgets() 
			progressMessageBar = qgis.utils.iface.messageBar().createMessage('Calculating area...')
			progressBar = QProgressBar()
			progressBar.setMaximum(100)
			progressMessageBar.layout().addWidget(progressBar)
			qgis.utils.iface.messageBar().pushWidget(progressMessageBar)
			self.progressMessageBar = progressMessageBar

			# start the worker in a new thread
			thread = QThread()
			worker.moveToThread(thread)
			worker.finished.connect(self.workerFinished)
			worker.error.connect(self.workerError)
			worker.progress.connect(progressBar.setValue)
			thread.started.connect(worker.run)
			thread.start()
			self.thread = thread
			self.worker = worker
			self.output = OutShape
	
	#Function to finished thread processing
	def workerFinished(self):
			
		# clean up the worker and thread
		self.worker.deleteLater()
		self.thread.quit()
		self.thread.wait()
		self.thread.deleteLater()
		LayerName = os.path.basename(self.output)[0:len(os.path.basename(self.output))-4]
		qgis.utils.iface.addVectorLayer(self.output,LayerName,"ogr")
		qgis.utils.iface.messageBar().clearWidgets()		
		QMessageBox.information(qgis.utils.iface.mainWindow(),"Calculate Area in Region","Process finished with successfully"+'\n'+'Layer:'+str(os.path.basename(self.output)[0:len(os.path.basename(self.output))-4])+" map added")

	#Function report error in work
	def workerError(self, e, exception_string):
		QgsMessageLog.logMessage('Worker thread raised an exception:\n'.format(exception_string), level=QgsMessageLog.CRITICAL)	
