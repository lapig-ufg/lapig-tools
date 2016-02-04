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
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QProgressBar, QMessageBox,QMenu
import PyQt4.QtGui
from PyQt4.QtCore import *

import os.path
import qgis.utils

class GenericTool():
	
	def __init__(self, iface):
		self.toolLabel = ''
		self.toolName = self.__class__.__name__
		
		self.iface = iface
		
		
		self.plugin_dir = os.path.dirname(__file__)
		self.icon_path = ":/plugins/LAPIGTools/icons/" + self.toolName + ".png"
		
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

	def initGui(self):
		self.obtainAction = QAction(QIcon(self.icon_path),QCoreApplication.translate(self.toolLabel,"&"+self.labelName), self.iface.mainWindow())
		QObject.connect(self.obtainAction, SIGNAL("triggered()"), self.run)
		return self.obtainAction,self.labelName
		
	def unload(self):
		#self.iface.removePluginMenu(self.toolLabel, self.obtainAction)
		self.iface.removeToolBarIcon(self.obtainAction)
