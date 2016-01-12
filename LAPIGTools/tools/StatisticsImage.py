# -*- coding: utf-8 -*-
"""
/***************************************************************************
 KappaIndex
								 A QGIS plugin
 Calculate kappa index from classification images
							  -------------------
		begin                : 2015-11-04
		git sha              : $Format:%H$
		copyright            : (C) 2015 by Bernard Silva
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QProgressBar, QMessageBox
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtCore
from GenericTool import GenericTool
from StatisticsImage_dialog import StatisticsImageDialog
from osgeo import ogr, gdal
import os,glob, string
import numpy
import qgis.utils


class Worker(QObject):
	'''Example worker for calculating the total area of all features in a layer'''
	
	def __init__(self, Folder, Stats, OutImage,NoData):
			QObject.__init__(self)
			self.killed = False
			
			self.Folder = Folder
			self.Stats = Stats
			self.OutImage = OutImage
			self.NoData = NoData
	
	def StatsImage(self):		

			#Input files
			source = os.path.join(self.Folder,"*.tif")
			output = self.OutImage
			listImages = glob.glob(source)
			NumberOfImages = len(listImages)
			
			#Get properties images
			Type = gdal.GDT_Float32
			driver = gdal.GetDriverByName('GTiff')
			setup = gdal.Open(listImages[0],gdal.GA_ReadOnly)
			Xsize = setup.RasterXSize 
			YSize = setup.RasterYSize
			proj = setup.GetProjection()
			geo = setup.GetGeoTransform()
			
			#Create output image
			ImageOut = driver.Create(output,Xsize,YSize,1,Type,['COMPRESS=LZW'])
			ImageOut.SetProjection(proj)
			ImageOut.SetGeoTransform(geo)			
			
			#Create log error file
			LogFolder = os.path.join(os.path.dirname(output),"Log.txt",)
			LogError = open(LogFolder,'w')
			
			BadImages = self.verifyDimension(listImages,Xsize,YSize)
			typeSt = self.Stats
			if BadImages == 0:
				Array = numpy.zeros((YSize,Xsize),dtype = numpy.float32)
				for i in xrange(YSize):
					aCom = numpy.zeros((NumberOfImages,1,Xsize))
									
					for j in xrange(len(listImages)):
						
						GetImages = gdal.Open(listImages[j],gdal.GA_ReadOnly)
						noDataDefault = GetImages.GetRasterBand(1).GetNoDataValue()
						band = GetImages.GetRasterBand(1).SetNoDataValue(noDataDefault)
						band = GetImages.GetRasterBand(1).ReadAsArray(0,i,Xsize,1)
						aCom[j] = band
						band = None
					if not self.NoData == '':
						aCom = numpy.where(aCom == float(self.NoData),None,aCom)		
										 
					aCom = self.CalcStats(typeSt,aCom,self.NoData)	
					Array[i,:] = aCom
								
					perc = int(100.00*(float(i+1)/float(YSize)))
					aCom = None
					self.progress.emit(perc)
								
				
				ImageOut.GetRasterBand(1).WriteArray(Array)
				
				if not self.NoData == '':
					ImageOut.GetRasterBand(1).SetNoDataValue(float(self.NoData))
				else:
					ImageOut.GetRasterBand(1).SetNoDataValue(noDataDefault)
				Array =None
					
				self.finished.emit(BadImages)
			else:
				self.finished.emit(BadImages)
		
	def CalcStats(self,stype,array,nodata):
		
		if stype == 0:
			if nodata == '':
				img = numpy.std(array,axis=0)
			else:
				img = numpy.nanstd(array,axis=0)
		
		elif stype == 1:
			if nodata == '':
				img = numpy.max(array,axis=0)
			else:
				img = numpy.nanmax(array,axis=0)

		elif stype == 2:
			if nodata == '':
				img = numpy.mean(array,axis=0)
			else:
				img = numpy.nanmean(array,axis=0)

		elif stype == 3:
			if nodata == '':
				img = numpy.var(array,axis=0)
			else:
				img = numpy.nanvar(array,axis=0)
		
		elif stype == 4:
			if nodata == '':
				img = numpy.min(array,axis=0)
			else:
				img = numpy.nanmin(array,axis=0)

		elif stype == 5:
			if nodata == '':
				img = numpy.sum(array,axis=0)
			else:
				img = numpy.nansum(array,axis=0)		

		return img
	
	def verifyDimension(self,list,XSize,YSize):
		Error = 0
		for i in list:
			GetImages = gdal.Open(i,gdal.GA_ReadOnly)
			if GetImages.RasterYSize != YSize and GetImages.RasterXSize != XSize:
				LogError.writelines(str(i))
				Error +=1
			GetImages = None
		return Error	

	def kill(self):
			self.killed = True			
	
	
	finished = pyqtSignal(int)
	error = pyqtSignal(Exception, basestring)
	progress = pyqtSignal(int)		


class StatisticsImage(GenericTool):
	"""QGIS Plugin Implementation."""

	def __init__(self,iface):
		GenericTool.__init__(self, iface)
		
		self.labelName = "Statistics Image in Batch"
		self.dlg = StatisticsImageDialog()
		
		self.dlg.lineEditFolder.clear()
		self.dlg.lineEditOutImage.clear()
		self.ListStats =['Standard Desviation','Maximum','Mean','Variance','Minimum','Sum']
		self.dlg.comboBoxStast.addItems(self.ListStats)
		self.dlg.pushButtonFolder.clicked.connect(self.InputFolder)
		self.dlg.pushButtonOutImage.clicked.connect(self.OutputImage)
	
	

	def run(self):
		"""Run method that performs all the real work"""
		
		# show the dialog
		self.dlg.show()
				
		# Run the dialog event loop
		result = self.dlg.exec_()
		Lista = ['Standard Desviation','Maximum','Mean','Variance','Minimum','Sum']
		# See if OK was pressed
		if result:
			
			iFolder = self.dlg.lineEditFolder.text()
			iSta = self.dlg.comboBoxStast.currentIndex()
			oImage = self.dlg.lineEditOutImage.text()
			NoData = self.dlg.lineEditNoData.text()
			self.startWorker(iFolder, iSta, oImage,NoData)
			
	#Function input folder shapes
	def InputFolder(self):        
			iFolder = QFileDialog.getExistingDirectory(self.dlg,'Insert Folder','',QFileDialog.ShowDirsOnly)
			self.dlg.lineEditFolder.setText(iFolder)

	#Function output shape file		
	def OutputImage(self):        
			filters = "TIFF (*.tif *.tiff)"
			oImage= QFileDialog.getSaveFileName(self.dlg,'Output Image','',filters)
			self.dlg.lineEditOutImage.setText(oImage+".tif")				
						
	
	#Function Start thread processing
	def startWorker(self, Folder, Stats, OutImage,NoData):
			
			# create a new worker instance
			worker = Worker(Folder,Stats, OutImage,NoData)

			#Create Progressbar
			qgis.utils.iface.messageBar().clearWidgets() 
			progressMessageBar = qgis.utils.iface.messageBar().createMessage('Calculating Statistics Image...')
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
			thread.started.connect(worker.StatsImage)
			thread.start()
			self.thread = thread
			self.worker = worker
			self.outImage = OutImage

	#Function to finished thread processing
	def workerFinished(self,value):
		
		# clean up the worker and thread
		self.worker.deleteLater()
		self.thread.quit()
		self.thread.wait()
		self.thread.deleteLater()
		qgis.utils.iface.messageBar().clearWidgets()						
		
		qgis.utils.iface.addRasterLayer(self.outImage,os.path.basename(self.outImage)[0:len(os.path.basename(self.outImage))-4])
		if value == 0:
			QMessageBox.information(qgis.utils.iface.mainWindow(),"Statistics Image","Processing sucessfully...")	
		else:
			QMessageBox.warming(qgis.utils.iface.mainWindow(),"Statistics Image","Image not same dimension...")	

	#Function report error in work
	def workerError(self, e, exception_string):
		QgsMessageLog.logMessage('Worker thread raised an exception:\n'.format(exception_string), level=QgsMessageLog.CRITICAL)	