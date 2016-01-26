# -*- coding: utf-8 -*-
"""
/***************************************************************************
StatisticsImage
								 A QGIS plugin
 Calculate StatisticsImage 
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
import os,glob, string, math, multiprocessing
import numpy
import qgis.utils
import utils

class Worker(QObject):
		
	def __init__(self,listImageIn,Stats,OutImage,NoData,YSizeStart, YSizeEnd, Xsize, nbands):
			
			QObject.__init__(self)
			self.killed = False
			self.Xsize = Xsize
			self.YSizeEnd = YSizeEnd
			self.YSizeStart = YSizeStart
			self.listImageIn = listImageIn
			self.Stats = Stats
			self.OutImage = OutImage
			self.NoData = NoData
			self.nbands = nbands 
	
	def StatsImage(self):		
			
			outWriter = gdal.Open(self.OutImage,gdal.GA_Update) 
			for i in xrange(self.YSizeStart,self.YSizeEnd):
				
				print i
				aCom = numpy.zeros((self.nbands,1,self.Xsize),dtype = numpy.float16)
				for j in xrange(0,self.nbands):
					GetImages = gdal.Open(self.listImageIn[j],gdal.GA_ReadOnly)
					aCom[j] = GetImages.GetRasterBand(1).ReadAsArray(0,i,self.Xsize,1)
							
				if len(self.NoData) > 0:
					aCom = numpy.where(aCom == float(self.NoData),None,aCom)													 
					
				aCom = self.CalcStats(self.Stats,aCom)																			
				outWriter.GetRasterBand(1).WriteArray(aCom,0,i)					
				
				if not self.NoData == '':
					outWriter.GetRasterBand(1).SetNoDataValue(float(self.NoData))
								
				aCom = None
				self.progress.emit()					
									
			self.finished.emit()
					
	def CalcStats(self,stype,array):
		
		if stype == 0:
			img = numpy.std(array,axis=0)
		
		elif stype == 1:
			img = numpy.max(array,axis=0)
		
		elif stype == 2:
			img = numpy.mean(array,axis=0)
		
		elif stype == 3:
			img = numpy.var(array,axis=0)
		
		elif stype == 4:
			img = numpy.min(array,axis=0)
		
		elif stype == 5:
			img = numpy.sum(array,axis=0)
		
		return img
	
	
	def kill(self):
			self.killed = True			
	
	
	finished = pyqtSignal()
	error = pyqtSignal(Exception, basestring)
	progress = pyqtSignal()		


class StatisticsImage(GenericTool):
	"""QGIS Plugin Implementation."""

	def __init__(self,iface):
		GenericTool.__init__(self, iface)
		
		self.labelName = "Statsistics Image in Batch"
		self.dlg = StatisticsImageDialog()
		
		self.dlg.lineEditFolder.clear()
		self.dlg.lineEditOutImage.clear()
		self.ListStats =['Standard Desviation','Maximum','Mean','Variance','Minimum','Sum']
		self.count = 0
		self.dlg.comboBoxStast.addItems(self.ListStats)
		self.dlg.pushButtonFolder.clicked.connect(self.InputFolder)
		self.dlg.pushButtonOutImage.clicked.connect(self.OutputImage)
	
	def setProgressBar(self):
		
		self.count += 1
		print "Count:"+str(self.count)
		self.globalYCount = self.count
		perc = int(100.00*(float(self.globalYCount)/float(self.YSize)))					
		self.progressBar.setValue(perc)


	def createProgressBar(self):
		
		#Create Progressbar
		qgis.utils.iface.messageBar().clearWidgets() 
		progressMessageBar = qgis.utils.iface.messageBar().createMessage('Executing Statistics Image...')
		self.progressBar = QProgressBar()
		self.progressBar.setMaximum(100)
		progressMessageBar.layout().addWidget(self.progressBar)
		qgis.utils.iface.messageBar().pushWidget(progressMessageBar)	


	def createWorkers(self, inFolder, outImage, Stats, Nodata):
		if type(Nodata) is float or Nodata == '': 	
			#Input files
			source = os.path.join(inFolder,"*.tif")
			listImages = sorted(glob.glob(source))
			NumberOfImages = len(listImages)
			
			#Get properties images
			Type = gdal.GDT_Float32
			driver = gdal.GetDriverByName('GTiff')
			setup = gdal.Open(listImages[0],gdal.GA_ReadOnly)
			Xsize = setup.RasterXSize 
			self.YSize = setup.RasterYSize
			proj = setup.GetProjection()
			geo = setup.GetGeoTransform()
			
			#Create output image
			ImageOut = driver.Create(outImage,Xsize,self.YSize,1,Type,['COMPRESS=LZW'])
			ImageOut.SetProjection(proj)
			ImageOut.SetGeoTransform(geo)			
			
			#Create log error file
			LogFolder = os.path.join(inFolder,"LogErros.txt",)
			LogError = open(LogFolder,'w')

			BadImages = utils.verifyImageDimension(listImages)
			typeSt = Stats
			
			if BadImages == 0:
				self.createProgressBar()
				
				ySizeInc = int(math.ceil(float(self.YSize) / float(self.threadNumber)))
				print ySizeInc, self.threadNumber
				for YSizeStart in xrange(0, self.YSize, ySizeInc):
					YSizeEnd = YSizeStart + ySizeInc

					if(YSizeEnd > self.YSize):
						YSizeEnd = self.YSize

					print(YSizeStart, YSizeEnd, ySizeInc)
					self.startWorker(listImages,Stats,outImage,Nodata,YSizeStart,YSizeEnd,Xsize,NumberOfImages)
			else:
				QMessageBox.warning(qgis.utils.iface.mainWindow(),"Statistic Image in Batch","Error in the images. Please, check the error log on:"+'\n'+os.path.join(os.path.dirname(inFolder),"LogErros.txt"))		
		else:
			QMessageBox.warning(qgis.utils.iface.mainWindow(),"Statistic Image in Batch","Nodata is not float number")


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
			self.oImage = self.dlg.lineEditOutImage.text()
			NoData = self.dlg.lineEditNoData.text()
			print NoData
			if len(NoData) > 0:
				NoData = float(NoData)
			
			self.threadNumber = multiprocessing.cpu_count()
			self.threadFinishedCount = 0
			self.createWorkers(iFolder, self.oImage, iSta, NoData)
			
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
	def startWorker(self,listImageIn,Stats,OutImage,NoData,YSizeStart, YSizeEnd, Xsize, nbands):
			
			# create a new worker instance
			worker = Worker(listImageIn,Stats,OutImage,NoData,YSizeStart, YSizeEnd, Xsize, nbands)
			
			# start the worker in a new thread
			thread = QThread()
			worker.moveToThread(thread)
			worker.finished.connect(self.workerFinished)
			worker.error.connect(self.workerError)
			worker.progress.connect(self.setProgressBar)
			thread.started.connect(worker.StatsImage)
			thread.start()
			self.thread = thread
			self.worker = worker
			

	#Function to finished thread processing
	def workerFinished(self):
		
		self.threadFinishedCount = self.threadFinishedCount + 1

		if self.threadFinishedCount == self.threadNumber:
			self.count = 0
			# clean up the worker and thread
			self.worker.deleteLater()
			self.thread.quit()
			self.thread.wait()
			self.thread.deleteLater()
			qgis.utils.iface.messageBar().clearWidgets()
			QMessageBox.information(qgis.utils.iface.mainWindow(),"Statistic Image in Batch","Processing sucessfully...")	

	#Function report error in work
	def workerError(self, e, exception_string):
		QgsMessageLog.logMessage('Worker thread raised an exception:\n'.format(exception_string), level=QgsMessageLog.CRITICAL)	