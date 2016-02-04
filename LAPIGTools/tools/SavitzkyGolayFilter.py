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
from scipy.signal import savgol_filter

class Worker(QObject):
	
	
	def __init__(self, inFolder,outFolder,WindowSize,Polynomial):
			QObject.__init__(self)
			self.killed = False
			
			self.inFolder = inFolder
			self.outFolder = outFolder
			self.WindowSize = WindowSize
			self.Polynomial = Polynomial
	
	def SavitzkyGolayFilter(self):		

			#Input files
			source = os.path.join(self.inFolder,"*.tif")
			desti = self.outFolder
			listImages = sorted(glob.glob(source))
			NumberOfImages = len(listImages)
		
			#Get properties images
			Type = gdal.GDT_Float32
			driver = gdal.GetDriverByName('GTiff')
			setup = gdal.Open(listImages[0],gdal.GA_ReadOnly)
			Xsize = setup.RasterXSize 
			YSize = setup.RasterYSize
			proj = setup.GetProjection()
			geo = setup.GetGeoTransform()
			listImageOut = []
			
			#Create output's images
			for li in listImages:				
				output = os.path.join(self.outFolder,os.path.basename(li))
				imageOut = driver.Create(output,Xsize,YSize,1,Type,['COMPRESS=LZW'])
				imageOut.SetProjection(proj)
				imageOut.SetGeoTransform(geo)
				listImageOut.append(imageOut)			
						
			BadImages = utils.verifyImageDimension(listImages)
			if BadImages == 0:
						
				for i in xrange(YSize):
					print i
					aCom = numpy.zeros((NumberOfImages,1,Xsize),numpy.float32)					
					for j in xrange(len(listImages)):
						GetImages = gdal.Open(listImages[j],gdal.GA_ReadOnly)
						aCom[j] = GetImages.GetRasterBand(1).ReadAsArray(0,i,Xsize,1)																	
					
					for k in xrange(Xsize):
						signal = aCom[numpy.array(range(NumberOfImages)),0,k]
						if numpy.max(signal) != numpy.min(signal):
							savGol = savgol_filter(signal,self.WindowSize,self.Polynomial)
							aCom[numpy.array(range(NumberOfImages)),0,k] = savGol																		
							
					for l in xrange(len(listImages)):						
						listImageOut[l].GetRasterBand(1).WriteArray(aCom[l],0,i)					
						
					perc = int(100.00*(float(i+1)/float(YSize)))					
					aCom = None			
					self.progress.emit(perc)
				self.finished.emit(0)
			else:
				self.finished.emit(BadImages)
		
	def kill(self):
			self.killed = True			
		
	finished = pyqtSignal(int)
	error = pyqtSignal(Exception, basestring)
	progress = pyqtSignal(int)		


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
		
		self.dlg.comboBoxWindow.addItems(self.ListWindow)
		self.dlg.comboBoxPoly.addItems(self.ListPolynomial)

		self.dlg.InButton.clicked.connect(self.InputFolder)
		self.dlg.outButton.clicked.connect(self.OutputImage)
		

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
			
			iFolder = self.dlg.lineEditInImages.text()
			oFolder = self.dlg.lineEditOutImages.text()
			Win = ListWin[self.dlg.comboBoxWindow.currentIndex()]
			Poly = ListPoly[self.dlg.comboBoxPoly.currentIndex()]
			if Win > Poly:
					self.startWorker(iFolder, oFolder, Win,Poly)	
			else:
					QMessageBox.warning(qgis.utils.iface.mainWindow(),"Savitzky Golay Filter","Polynomial Order must be less than window size ")
			

	#Function input folder images
	def InputFolder(self):        
			iFolder = QFileDialog.getExistingDirectory(self.dlg,'Insert Folder','',QFileDialog.ShowDirsOnly)
			self.dlg.lineEditInImages.setText(iFolder)

	#Function output folder images		
	def OutputImage(self):        
			oImage = QFileDialog.getExistingDirectory(self.dlg,'Output Folder','',QFileDialog.ShowDirsOnly)
			self.dlg.lineEditOutImages.setText(oImage)				
						
	
	#Function Start thread processing
	def startWorker(self, inFolder, OutFolder, Window, Polynomial):
			
			# create a new worker instance
			worker = Worker(inFolder, OutFolder, Window, Polynomial)

			#Create Progressbar
			qgis.utils.iface.messageBar().clearWidgets() 
			progressMessageBar = qgis.utils.iface.messageBar().createMessage('Executing Savitzky Golay Filter...')
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
			thread.started.connect(worker.SavitzkyGolayFilter)
			thread.start()
			self.thread = thread
			self.worker = worker
			

	#Function to finished thread processing
	def workerFinished(self,value):
		
		# clean up the worker and thread
		self.worker.deleteLater()
		self.thread.quit()
		self.thread.wait()
		self.thread.deleteLater()
		qgis.utils.iface.messageBar().clearWidgets()						
			
		if value == 0:
			QMessageBox.information(qgis.utils.iface.mainWindow(),"Savitzky Golay Filter","Processing sucessfully...")	
		else:
			QMessageBox.warning(qgis.utils.iface.mainWindow(),"Savitzky Golay Filter","Error in the images. Please, check the error log on:"+'\n'+os.path.join(self.dlg.lineEditInImages.text(),"LogErros.txt"))	

	#Function report error in work
	def workerError(self, e, exception_string):
		QgsMessageLog.logMessage('Worker thread raised an exception:\n'.format(exception_string), level=QgsMessageLog.CRITICAL)	