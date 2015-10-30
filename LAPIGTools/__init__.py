# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CalculateRegion
                                 A QGIS plugin
 This tool is create from Geoprocessind and Image Processing Laboratory from University of Goias (Brazil)
                             -------------------
        begin                : 2015-10-30
        copyright            : (C) 2015 by Bernard Silva de Oliveira - LAPIG/UFG
        email                : so_geoprocessamento@yahoo.com.br
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load CalculateRegion class from file CalculateRegion.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .CalculateRegion import CalculateRegion
    return CalculateRegion(iface)
