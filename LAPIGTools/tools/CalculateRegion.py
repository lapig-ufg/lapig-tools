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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication,QThread, QObject, pyqtSignal,SIGNAL
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QProgressBar, QMessageBox
import PyQt4.QtGui
from PyQt4.QtCore import *
from CalculateRegion_dialog import CalculateRegionDialog
from GenericTool import GenericTool

import os.path
import glob, os
import qgis.utils, qgis.gui
from osgeo import ogr, osr


class Worker(QObject):
		
	def __init__(self, ExtrairShape, CalcShape, OutShape, Coordref, TypeUnits):
			QObject.__init__(self)
			self.killed = False
			self.ExtrairShape = ExtrairShape
			
			self.CalcShape = CalcShape
			self.OutShape = OutShape
			self.Coorref = Coordref
			self.TypeUnits = TypeUnits
			

	def runCalc(self):
			
			listShapes = sorted(glob.glob(os.path.join(self.ExtrairShape,'*.shp')))
			drv = ogr.GetDriverByName('ESRI ShapeFile')
			logfile = os.path.join(os.path.dirname(self.OutShape),"LogErros.txt")
			logerrortxt = open(logfile,"w")
						
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
				if not os.path.exists(m[0:-4]+".qix"):
					nametale = os.path.basename(m)[0:-4]
					os.system('ogrinfo -sql "CREATE SPATIAL INDEX ON '+nametale+'"'+" "+str(m))
				FieldName = str(os.path.basename(m)[len(os.path.basename(m))-13:len(os.path.basename(m))-4])
				field = ogr.FieldDefn(FieldName,ogr.OFTReal)
				field.SetWidth(20)    
				field.SetPrecision(6)
				layer.CreateField(field)
				ListFieldName.append(FieldName)
				FieldName = None
			DicError = {}
			
			#Add Sum Field
			field = ogr.FieldDefn('SUM',ogr.OFTReal)
			field.SetWidth(20)    
			field.SetPrecision(6)
			layer.CreateField(field)
			
			for shape in listShapes:				
					DicError[os.path.basename(shape)] = ''	
			
			#Calculating Area
			for i in range(countRows):
													
					gLayer = layer.GetFeature(i)
					geom1 = gLayer.GetGeometryRef()
					X1,X2,Y1,Y2 = geom1.GetEnvelope()
					Sum = 0.00
					for (k,m) in zip(listShapes,range(len(listShapes))):
						
						AreaDes = 0.00
						oDes = drv.Open(k,0)
						olayer = oDes.GetLayer(0)
						olayer.SetSpatialFilterRect(X1,Y1,X2,Y2)
						feat2 = olayer.GetNextFeature()
						
						while feat2:
							geom2 = feat2.GetGeometryRef()
							
							try:
								if geom2.Intersects(geom1):
									
									if not geom2.Within(geom1):
										geom2 = geom2.Intersection(geom1)						 
										
									SourSr = osr.SpatialReference()
									SourSr.ImportFromWkt(geom2.GetSpatialReference().ExportToWkt())								
									
									destSR = osr.SpatialReference()
									EPSGOut = int(self.Coorref[5:len(self.Coorref)])
									destSR.ImportFromEPSG(EPSGOut)
																	
									geom2.Transform(osr.CoordinateTransformation(SourSr,destSR))
									AreaDes += self.CalcArea(self.TypeUnits,geom2.GetArea())
									
							except:
								DicError[os.path.basename(k)] += str(feat2.GetFID())+' '
							feat2.Destroy()
							feat2 = olayer.GetNextFeature()
			
						gLayer.SetField(ListFieldName[m],AreaDes)
						layer.SetFeature(gLayer)
						oDes.Destroy()
						Sum += AreaDes
			
					#Add sum values
					gLayer.SetField('SUM',Sum)
					layer.SetFeature(gLayer)
					perc = int(100.00*(float(i+1)/float(countRows)))
					self.progress.emit(perc)
			
			CountErros = 0		
			for key, values in DicError.iteritems():
				countpolygon = len(DicError[key])
				if countpolygon > 0:	
					logerrortxt.writelines(str(key)+'\n')
					logerrortxt.writelines('FIDs:'+str(DicError[key])+'\n')
					logerrortxt.writelines('Sum bad polygons:'+str(countpolygon)+'\n')
					logerrortxt.writelines('\n')
					CountErros += countpolygon
			ListFieldName = None	
			logerrortxt.close()
			self.finished.emit(CountErros)
			 
	
	def kill(self):
			self.killed = True
	
	def CalcArea(self,Type,Value):
			if Type == 'Hectares':
				return Value/10000.00
			elif Type == 'Square meters':
				return Value
			elif Type == 'Square kilometers': 
				return Value/1000000.00		

	finished = pyqtSignal(int)
	error = pyqtSignal(Exception, basestring)
	progress = pyqtSignal(int)
	
class CalculateRegion(GenericTool):
	"""QGIS Plugin Implementation."""

	def __init__(self, iface):
		GenericTool.__init__(self, iface)
		
		self.labelName = "Calculate Area in Region"
		self.dlg = CalculateRegionDialog()
		
		self.dlg.lineEditShapeClip.clear()
		self.dlg.lineEditFolder.clear()
		self.dlg.lineEditShapeOut.clear()
		self.dlg.lineEditCoordRef.clear()
		
		self.dlg.pushButtonShape.clicked.connect(self.InputShape)
		self.dlg.pushButtonFolder.clicked.connect(self.InputFolder)
		self.dlg.pushButtonShapeOut.clicked.connect(self.OutputShape)
		self.dlg.pushButtonCoordRef.clicked.connect(self.SelectCoordSystem)
		
		
		self.ListUnits = ['Square meters','Square kilometers','Hectares']
		self.dlg.Units.addItems(self.ListUnits)
		
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
			Ref = self.dlg.lineEditCoordRef.text()
			self.startWorker(ExtrairShape, CalcShape, OutShape, Ref, TypeUnits)
	
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
	
	def SelectCoordSystem(self):
			projection = None
			projection = qgis.gui.QgsGenericProjectionSelector()
			teste = projection.exec_()
			EPSG = projection.selectedAuthId()
			self.dlg.lineEditCoordRef.setText(EPSG)
			
			
	
	#Function Start thread processing
	def startWorker(self, ExtrairShape, CalcShape, OutShape, Ref, TypeUnits):
			
			# create a new worker instance
			worker = Worker(ExtrairShape, CalcShape, OutShape, Ref, TypeUnits)

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
			thread.started.connect(worker.runCalc)
			thread.start()
			self.thread = thread
			self.worker = worker
			self.output = OutShape
			
	#Function to finished thread processing
	def workerFinished(self,value):
		
		# clean up the worker and thread
		self.worker.deleteLater()
		self.thread.quit()
		self.thread.wait()
		self.thread.deleteLater()
		LayerName = os.path.basename(self.output)[0:len(os.path.basename(self.output))-4]
		qgis.utils.iface.addVectorLayer(self.output,LayerName,"ogr")
		qgis.utils.iface.messageBar().clearWidgets()		
		
		
		if value > 0:
			QMessageBox.warning(qgis.utils.iface.mainWindow(),"Calculate Area in Region",'There '+str(value)+
													' geometries not valid. For more information see the log file at:'+os.path.join(os.path.dirname(self.output),"LogErros.txt"))
		else:
			QMessageBox.information(qgis.utils.iface.mainWindow(),"Calculate Area in Region","Process finished with successfully"+
															'\n'+'Layer:'+str(os.path.basename(self.output)[0:len(os.path.basename(self.output))-4])+" map added")
	#Function report error in work
	def workerError(self, e, exception_string):
		QgsMessageLog.logMessage('Worker thread raised an exception:\n'.format(exception_string), level=QgsMessageLog.CRITICAL)	
