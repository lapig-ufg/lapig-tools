# -*- coding: utf-8 -*-
"""
/***************************************************************************
 KappaIndex
								 A QGIS plugin
 Calculate kappa index
							  -------------------
		begin                : 2015-10-25
		git sha              : $Format:%H$
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
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtCore

from GenericTool import GenericTool
from KappaIndex_dialog import KappaIndexDialog
import os.path
import qgis.utils
from osgeo import ogr
import sys, os, string, math




class KappaIndex(GenericTool):
	"""QGIS Plugin Implementation."""

	def __init__(self, iface):
		GenericTool.__init__(self, iface)

		self.labelName = "Kappa Index"

		self.canvas = self.iface.mapCanvas()
		self.dlg = KappaIndexDialog()
	
		self.insertCombox()	
		self.insertComboxField()

		self.dlg.ButtonOutMat.clicked.connect(self.InputCSV)

		QObject.connect(self.canvas, SIGNAL("layersChanged ()"), self.insertCombox)
		QObject.connect(self.dlg.comboBoxLayer, SIGNAL("currentIndexChanged(int)"), self.insertComboxField)

	def insertCombox(self):
		global listObject
		global listLayers
		self.dlg.comboBoxLayer.clear()
		if len(self.canvas.layers()) > 0:
			listLayers = []
			listObject = []
			for layer in self.canvas.layers():
				if layer.type() == 0:
					listLayers.append(layer.name())
					listObject.append(layer)  
			self.dlg.comboBoxLayer.addItems(listLayers)

	def insertComboxField(self):
		self.dlg.comboBoxField1.clear()
		self.dlg.comboBoxField2.clear()
		if not self.dlg.comboBoxLayer.currentIndex() == -1:
			selectlayer = listObject[self.dlg.comboBoxLayer.currentIndex()]
			fields = selectlayer.pendingFields()
			self.ListFields = []
			for field in fields:
				self.ListFields.append(field.name())	
			self.dlg.comboBoxField1.addItems(self.ListFields)
			self.dlg.comboBoxField2.addItems(self.ListFields)
	
	#Function input clip shape file		
	def InputCSV(self):
			filters = "CSV (*.csv)"
			iCSV = QFileDialog.getSaveFileName(self.dlg,'Output Kappa Matrix','',filters)
			if not iCSV == '':
				iCSV = iCSV.replace(".csv","")
				self.dlg.lineEdit.setText(iCSV+".csv")	
	
	def run(self):
		"""Run method that performs all the real work"""
		
		# show the dialog
		self.dlg.show()
				
		# Run the dialog event loop
		result = self.dlg.exec_()
		
		# See if OK was pressed
		if result:
			
			x = 0
			y = 0
			
			
			Field1 = int(self.dlg.comboBoxField1.currentIndex())
			Field2 = int(self.dlg.comboBoxField2.currentIndex())	
				
			selectedfile = listObject[self.dlg.comboBoxLayer.currentIndex()]
						
			count = [row for row in selectedfile.getFeatures()]
			fc_conc = len(count)
			Total_obs = fc_conc

			# configure the QgsMessageBar
			qgis.utils.iface.messageBar().clearWidgets() 
			progressMessageBar = qgis.utils.iface.messageBar().createMessage('Calculating Kappa Index...')
			progressBar = QProgressBar()
			progressBar.setMaximum(fc_conc)
			progressMessageBar.layout().addWidget(progressBar)
			qgis.utils.iface.messageBar().pushWidget(progressMessageBar)
			
			aValues1 = []
			aValues2 = []
			class_temp = ""
			Class = []
			class_desc = []
										
			#Initial Variable progress bar
			count = 1
			
			for fld in selectedfile.getFeatures():
				aValues1.append(str(fld[Field1]))
				aValues2.append(str(fld[Field2]))
				Class.append(str(fld[Field1]))
				Class.append(str(fld[Field2]))
				Class = list(set(Class))
				Class.sort()

				progressBar.setValue(count)
				count +=1


			TotalClasses = len(Class)
			
			# Create a matrix Class, adding a row/column for the labels, and one for the totals.
			Eixos = TotalClasses + 2
			
			matrixKappa = [[0 for col in range(Eixos)] for row in range(Eixos)]
			matrixKappa[0][0] = "#"
			matrixKappa[0][Eixos-1] = Field2
			matrixKappa[Eixos-1][0] = Field1
			matrixKappa[Eixos-1][Eixos-1] = Total_obs
			while x < TotalClasses:
				matrixKappa[x+1][0] = Class[x]
				matrixKappa[0][x+1] = Class[x]
				x += 1
			
			x = 0
			for sample in range(Total_obs):
				Obs_temp1 = aValues1[sample]
				Obs_temp2 = aValues2[sample]
				for col in range(TotalClasses):
					for row in range(TotalClasses):
						col_temp = matrixKappa[col-col][row+1]
						row_temp = matrixKappa[col+1][row-row]
						if ((col_temp == aValues2[sample]) and (row_temp == aValues1[sample])):
							matrixKappa[col+1][row+1] += 1
							matrixKappa[Eixos-1][row+1] += 1
							matrixKappa[col+1][Eixos-1] += 1
			
			
			# Find the chance agreement
			Chance_agree = 0.0
			chance1 = 0.00
			chance2 = 0.00
			per_chance = ""
			per_chance2 = ""
			for row in range(TotalClasses):
					chance1 = float(matrixKappa[Eixos-1][row+1])/float(matrixKappa[Eixos-1][Eixos-1])
					per_chance = " (" + str(round(chance1*100,1)) + "%)"
					matrixKappa[Eixos-1][row+1] = str(matrixKappa[Eixos-1][row+1]) + str(per_chance)                                                    
					chance2 = float(matrixKappa[row+1][Eixos-1])/float(matrixKappa[Eixos-1][Eixos-1])
					per_chance2 = " (" + str(round(chance2*100,1)) + "%)"
					matrixKappa[row+1][Eixos-1] = str(matrixKappa[row+1][Eixos-1]) + str(per_chance2)
					chance_temp = chance1*chance2
					Chance_agree += chance_temp
			
			
			# Find the observed agreement      
			Observed_total = 0.0
			for i in range(TotalClasses):
				Observed_total += matrixKappa[i+1][i+1]
			
			Observed_agreement = (Observed_total/Total_obs)
			
			# Find the Kappa Coefficient
			Kappa_coef = ((Observed_agreement - Chance_agree)/(1 - Chance_agree))
			
			#Outfile kappa matrix
			Kappafile = self.dlg.lineEdit.text()
			mat_kappa = open(Kappafile,"w")
			mat_kappa.writelines('Accuracy Global: '+str(round(Observed_agreement*100, 2)))
			mat_kappa.writelines('\n')
			mat_kappa.writelines('Kappa Index: %.2f '%Kappa_coef)
			mat_kappa.writelines('\n')
			mat_kappa.writelines('\n')

			#Generate Kappa Matrix
			for line in matrixKappa:
				for elements in line:
					mat_kappa.writelines(str(elements)+'\t')
				mat_kappa.writelines('\n')		
			
			mat_kappa.close()
			
			qgis.utils.iface.messageBar().clearWidgets()
			QMessageBox.information(qgis.utils.iface.mainWindow(),"Kappa Index","Process finished with successfully"+'\n'+"Accuracy Global: "+str(round(Observed_agreement*100, 2)) + "%"+'\n'+
									"Kappa Coefficient: %.2f"%Kappa_coef)
			