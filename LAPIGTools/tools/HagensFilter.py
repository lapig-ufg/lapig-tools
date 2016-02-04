from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QProgressBar, QMessageBox
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtCore
from GenericTool import GenericTool
from HagensFilter_dialog import HagensFilterDialog
from osgeo import ogr, gdal
import os,glob, string
import numpy
import qgis.utils
import utils
import HagensFilter_tools

class Worker(QObject):
		
	def __init__(self, inFolder, inFlag, outFolder,Composite):
			
			QObject.__init__(self)
			self.killed = False
			
			self.inFolder = inFolder
			self.inFlag = inFlag
			self.outFolder = outFolder
			self.Composite = Composite	
	
	def HagensFilterCalc(self):		
			
			BadImages = utils.verifyImageDimension(self.inFolder)							
			if BadImages == 0:
				
				#Get properties images
				Type = gdal.GDT_Float32
				driver = gdal.GetDriverByName('GTiff')
				setup = gdal.Open(self.inFolder[0],gdal.GA_ReadOnly)
				Xsize = setup.RasterXSize 
				YSize = setup.RasterYSize
				proj = setup.GetProjection()
				geo = setup.GetGeoTransform()
				listImageOut = []				
				
				#Create output's images
				for li in self.inFolder:				
					output = os.path.join(self.outFolder,os.path.basename(li))
					imageOut = driver.Create(output,Xsize,YSize,1,Type,['COMPRESS=LZW'])
					imageOut.SetProjection(proj)
					imageOut.SetGeoTransform(geo)
					listImageOut.append(imageOut)										
				
				#Create typical year
				tYear = os.path.join(self.outFolder,'TypicalYear.tif')
				typicalYearImage = driver.Create(tYear,Xsize,YSize,self.Composite,Type,['COMPRESS=LZW'])
				typicalYearImage.SetProjection(proj)
				typicalYearImage.SetGeoTransform(geo)
				
				#Create images Quality pixels - Used in Create typical year
				iQuality = os.path.join(self.outFolder,'QualityTypicalYear.tif')
				imageQuality = driver.Create(iQuality,Xsize,YSize,self.Composite,Type,['COMPRESS=LZW'])
				imageQuality.SetProjection(proj)
				imageQuality.SetGeoTransform(geo)
				
				NumberOfImages = len(self.inFolder)	
				
				#Process BIL
				for i in xrange(YSize):					
					iArray = numpy.zeros((NumberOfImages,1,Xsize),numpy.float32)					
					iFlag = numpy.zeros((NumberOfImages,1,Xsize),numpy.byte)						
										
					#Get Values in Image
					for j in xrange(len(self.inFolder)):
						
						GetImages = gdal.Open(self.inFolder[j],gdal.GA_ReadOnly)
						GetImagesFlags = gdal.Open(self.inFlag[j],gdal.GA_ReadOnly)							
						iArray[j] = GetImages.GetRasterBand(1).ReadAsArray(0,i,Xsize,1)																							
						iFlag[j] = GetImagesFlags.GetRasterBand(1).ReadAsArray(0,i,Xsize,1) 	
					
					#Products Hagens Filter
					typicalYear = HagensFilter_tools.AveregeYearDoy(iArray,iFlag,self.Composite,0,Xsize)[0]
					arrayQA = HagensFilter_tools.AveregeYearDoy(iArray,iFlag,self.Composite,0,Xsize)[1]
					devAveregeAnual	= HagensFilter_tools.DevAveregeAnual(iArray,iFlag,self.Composite,typicalYear,0,Xsize)	
					devNeighborhoodDay = HagensFilter_tools.DevNeighborhoodDay(iArray,iFlag,0,Xsize)
					devNeighborhoodAnual = HagensFilter_tools.DevNeighborhoodAnual(iArray,iFlag,self.Composite,0,Xsize)	
					fillGaps = HagensFilter_tools.FillGaps(iArray,iFlag,self.Composite,typicalYear,devAveregeAnual,devNeighborhoodDay,devNeighborhoodAnual,0,Xsize)

					#Update Typical Year
					for k in xrange(int(self.Composite)):
						
						typicalYearImage.GetRasterBand(k+1).WriteArray(typicalYear[k],0,i)
						imageQuality.GetRasterBand(k+1).WriteArray(arrayQA[k],0,i)

					#Update Hagens Filter
					for l in xrange(len(self.inFolder)):						
						listImageOut[l].GetRasterBand(1).WriteArray(fillGaps[l],0,i)																		
						
					perc = int(100.00*(float(i+1)/float(YSize)))					
					iArray = None			
					iFlag = None
					
					self.progress.emit(perc)
				
				self.finished.emit(0)
			else:
				self.finished.emit(BadImages)
		
			
	def kill(self):
			self.killed = True			
		
	finished = pyqtSignal(int)
	error = pyqtSignal(Exception, basestring)
	progress = pyqtSignal(int)		


class HagensFilter(GenericTool):
	"""QGIS Plugin Implementation."""

	def __init__(self,iface):
		GenericTool.__init__(self, iface)
		
		self.labelName = "Hagens Filter"
		self.dlg = HagensFilterDialog()
		
		self.dlg.lineEditImages.clear()
		self.dlg.lineEditFlags.clear()
		self.dlg.lineEditOut.clear()
		self.dlg.lineEditOutComposite.clear()
		
		self.dlg.pushButtonImages.clicked.connect(self.InputFolder)
		self.dlg.pushButtonFlags.clicked.connect(self.InputFolderFlags)
		self.dlg.pushButtonOut.clicked.connect(self.OutputImage)
		

	def run(self):
		"""Run method that performs all the real work"""
		
		# show the dialog
		self.dlg.show()
				
		# Run the dialog event loop
		result = self.dlg.exec_()
		
		# See if OK was pressed
		if result:
			
			iFolder = self.dlg.lineEditImages.text()
			iFlag = self.dlg.lineEditFlags.text()
			oFolder = self.dlg.lineEditOut.text()
			Composite = self.dlg.lineEditOutComposite.text()
			if (len(Composite)==0) or (len(iFolder)==0) or (len(iFlag)==0) or (len(oFolder)==0):
					QMessageBox.warning(qgis.utils.iface.mainWindow(),"Hagens Filter","        Fields empty        ")
			else:
								
				ListInput = sorted(glob.glob(os.path.join(iFolder,"*.tif")))
				ListFlags = sorted(glob.glob(os.path.join(iFlag,"*.tif")))
				
				Nbands = len(ListInput)
				NbandsFlags = len(ListFlags)
				if Nbands == NbandsFlags:
					try:
						Composite = int(Composite)				
						self.startWorker(ListInput,ListFlags,oFolder,Composite)
					except:
						QMessageBox.warning(qgis.utils.iface.mainWindow(),"Hagens Filter","Image fo Year is not integer")
				else:
					QMessageBox.warning(qgis.utils.iface.mainWindow(),"Hagens Filter","Number of input images is higher or lower than the images flags")
			
	#Function input folder images
	def InputFolder(self):        
			iFolder = QFileDialog.getExistingDirectory(self.dlg,'Insert Folder Images','',QFileDialog.ShowDirsOnly)
			self.dlg.lineEditImages.setText(iFolder)

	#Function input folder flags
	def InputFolderFlags(self):        
			iFolder = QFileDialog.getExistingDirectory(self.dlg,'Insert Folder Flags','',QFileDialog.ShowDirsOnly)
			self.dlg.lineEditFlags.setText(iFolder)

	#Function output folder images		
	def OutputImage(self):        
			oFolder = QFileDialog.getExistingDirectory(self.dlg,'Output Folder','',QFileDialog.ShowDirsOnly)
			self.dlg.lineEditOut.setText(oFolder)				
						
	#Function Start thread processing
	def startWorker(self, inFolder, inFlag, outFolder,Composite):
			
			# create a new worker instance
			worker = Worker(inFolder, inFlag, outFolder,Composite)

			#Create Progressbar
			qgis.utils.iface.messageBar().clearWidgets() 
			progressMessageBar = qgis.utils.iface.messageBar().createMessage('Executing Hagens Filter...')
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
			thread.started.connect(worker.HagensFilterCalc)
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
			QMessageBox.information(qgis.utils.iface.mainWindow(),"Hagens Filter","Processing sucessfully...")	
		else:
			QMessageBox.warning(qgis.utils.iface.mainWindow(),"Hagens Filter","Error in the images. Please, check the error log on:"+'\n'+os.path.join(self.dlg.lineEditImages.text(),"LogErros.txt"))	

	#Function report error in work
	def workerError(self, e, exception_string):
		QgsMessageLog.logMessage('Worker thread raised an exception:\n'.format(exception_string), level=QgsMessageLog.CRITICAL)	