# -*- coding: utf-8 -*-
"""
/***************************************************************************
SavitzkyGolayFilter
								 A QGIS plugin
 Smooth images(Time Series) applied method Savitzky Golay.
							  -------------------
		begin                : 2016-01-18
		git sha              : $Format:%H$
		copyright            : (C) 2016 by Bernard Silva
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
from SavitzkyGolayFilter_dialog import SavitzkyGolayFilterDialog
from osgeo import ogr, gdal
import os,glob, string
import numpy
import qgis.utils
import utils
import math
import multiprocessing
from scipy.signal import savgol_filter


class Worker(QObject):
	
	
	def __init__(self, listImageIn, listImageOut, YSizeStart, YSizeEnd, Xsize, WindowSize, Polynomial ):
		QObject.__init__(self)
		self.killed = False
		
		self.Xsize = Xsize
		self.YSizeEnd = YSizeEnd
		self.YSizeStart = YSizeStart
		self.WindowSize = WindowSize
		self.Polynomial = Polynomial
		self.listImageIn = listImageIn
		self.listImageOut = listImageOut
		
	def SavitzkyGolayFilter(self):		

		NumberOfImages = len(self.listImageIn)
		
		for i in xrange(self.YSizeStart, self.YSizeEnd):
			print i
			aCom = numpy.zeros((NumberOfImages,1,self.Xsize),numpy.float32)					
			for j in xrange(len(self.listImageIn)):
				GetImages = gdal.Open(self.listImageIn[j],gdal.GA_ReadOnly)
				aCom[j] = GetImages.GetRasterBand(1).ReadAsArray(0,i,self.Xsize,1)																	
			
			for k in range(self.Xsize):
				signal = aCom[numpy.array(range(NumberOfImages)),0,k]
				savGol = savgol_filter(signal,self.WindowSize,self.Polynomial)
				aCom[numpy.array(range(NumberOfImages)),0,k] = savGol																		
					
			for l in xrange(len(self.listImageIn)):						
				self.listImageOut[l].GetRasterBand(1).WriteArray(aCom[l],0,i)					
				
			aCom = None			
			self.progress.emit()
			
		self.finished.emit()
		
	finished = pyqtSignal()
	error = pyqtSignal(Exception, basestring)
	progress = pyqtSignal()		


class SavitzkyGolayFilter(GenericTool):
	"""QGIS Plugin Implementation."""
	
	
	def __init__(self,iface):
		GenericTool.__init__(self, iface)
		
		self.labelName = "Savitzky Golay Filter"
		self.dlg = SavitzkyGolayFilterDialog()
		
		self.dlg.lineEditInImages.clear()
		self.dlg.lineEditOutImages.clear()
		self.ListWindow =['3','5','7','9']
		self.ListPolynomial =['1','2','3','4','5']
		self.count = 0
		self.dlg.comboBoxWindow.addItems(self.ListWindow)
		self.dlg.comboBoxPoly.addItems(self.ListPolynomial)

		self.dlg.InButton.clicked.connect(self.InputFolder)
		self.dlg.outButton.clicked.connect(self.OutputImage)
	
	def setProgressBar(self):
		
		self.count += 1
		print "Count:"+str(self.count)
		self.globalYCount = self.count
		perc = int(100.00*(float(self.globalYCount)/float(self.YSize)))					
		self.progressBar.setValue(perc)

	def createProgressBar(self):
		
		#Create Progressbar
		qgis.utils.iface.messageBar().clearWidgets() 
		progressMessageBar = qgis.utils.iface.messageBar().createMessage('Executing Savitzky Golay Filter...')
		self.progressBar = QProgressBar()
		self.progressBar.setMaximum(100)
		progressMessageBar.layout().addWidget(self.progressBar)
		qgis.utils.iface.messageBar().pushWidget(progressMessageBar)
		
	def createWorkers(self, inFolder, outFolder, WindowSize, Polynomial):
		
		if WindowSize > Polynomial:	
			
			#Input files
			source = os.path.join(inFolder,"*.tif")
			desti = outFolder
			listImageIn = sorted(glob.glob(source))
			NumberOfImages = len(listImageIn)

			#Get properties images
			setup = gdal.Open(listImageIn[0],gdal.GA_ReadOnly)
			
			Xsize = setup.RasterXSize 
			proj = setup.GetProjection()
			geo = setup.GetGeoTransform()
			
			self.YSize = setup.RasterYSize

			listImageOut = []
			Type = gdal.GDT_Float32
			driver = gdal.GetDriverByName('GTiff')
			#Create output's images
			for li in listImageIn:				
				output = os.path.join(outFolder,os.path.basename(li))
				imageOut = driver.Create(output,Xsize,self.YSize,1,Type,['COMPRESS=LZW'])
				imageOut.SetProjection(proj)
				imageOut.SetGeoTransform(geo)
				listImageOut.append(imageOut)			
						
			BadImages = utils.verifyImageDimension(listImageIn)
			if BadImages == 0:
				self.createProgressBar()
				
				ySizeInc = int(math.ceil(float(self.YSize) / float(self.threadNumber)))
				for YSizeStart in xrange(0, self.YSize, ySizeInc):
					YSizeEnd = YSizeStart + ySizeInc

					if(YSizeEnd > self.YSize):
						YSizeEnd = self.YSize

					print(YSizeStart, YSizeEnd, ySizeInc)
					self.startWorker(listImageIn, listImageOut, YSizeStart, YSizeEnd, Xsize, WindowSize, Polynomial)

			else:
				QMessageBox.warning(qgis.utils.iface.mainWindow(),"Savitzky Golay Filter","Error in the images. Please, check the error log on:"+'\n'+os.path.join(os.path.dirname(inFolder),"LogErros.txt"))		
		else:
			QMessageBox.warning(qgis.utils.iface.mainWindow(),"Savitzky Golay Filter","Polynomial Order must be less than window size ")

	def run(self):
		"""Run method that performs all the real work"""
		
		# show the dialog
		self.dlg.show()
				
		# Run the dialog event loop
		result = self.dlg.exec_()
		ListWin = [3,5,7,9]
		ListPoly = [1,2,3,4,5]
		# See if OK was pressed
		if result:
			
			inFolder = self.dlg.lineEditInImages.text()
			outFolder = self.dlg.lineEditOutImages.text()
			WindowSize = ListWin[self.dlg.comboBoxWindow.currentIndex()]
			Polynomial = ListPoly[self.dlg.comboBoxPoly.currentIndex()]
			#if Win > Poly:

			self.threadNumber = multiprocessing.cpu_count()
			self.threadFinishedCount = 0
			self.createWorkers(inFolder, outFolder, WindowSize, Polynomial)
			#else:

	#Function input folder images
	def InputFolder(self):        
			iFolder = QFileDialog.getExistingDirectory(self.dlg,'Insert Folder','',QFileDialog.ShowDirsOnly)
			self.dlg.lineEditInImages.setText(iFolder)

	#Function output folder images		
	def OutputImage(self):        
			oImage = QFileDialog.getExistingDirectory(self.dlg,'Insert Folder','',QFileDialog.ShowDirsOnly)
			self.dlg.lineEditOutImages.setText(oImage)				
						
	
	#Function Start thread processing
	def startWorker(self, listImageIn, listImageOut, YSizeStart, YSizeEnd, Xsize, WindowSize, Polynomial):
			
		# create a new worker instance
		worker = Worker(listImageIn, listImageOut, YSizeStart, YSizeEnd, Xsize, WindowSize, Polynomial)

		# start the worker in a new thread
		thread = QThread()
		worker.moveToThread(thread)
		worker.finished.connect(self.workerFinished)
		worker.error.connect(self.workerError)
		worker.progress.connect(self.setProgressBar)
		thread.started.connect(worker.SavitzkyGolayFilter)
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
			QMessageBox.information(qgis.utils.iface.mainWindow(),"Savitzky Golay Filter","Processing sucessfully...")	
			

	#Function report error in work
	def workerError(self, e, exception_string):
		QgsMessageLog.logMessage('Worker thread raised an exception:\n'.format(exception_string), level=QgsMessageLog.CRITICAL)	