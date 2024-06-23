# Pod Repositioning Problem
# Copyright (C) 2017, 2018 Arbeitsgruppe OR an der Leuphana Universität Lüneburg
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Here are some frequently used functions which have nothing to do with the optimization problem.

.. moduleauthor:: Ruslan Krenzler

25 Juni 2018
"""
import os.path


def create_missing_directories_of_file(file_path):
    """Create directory missing in the path file_path.

    The last file in the file_path is ignored.
    The directories are created recursively.
    """
    directory = os.path.dirname(file_path)
    if directory != "":
        if not os.path.exists(directory):
            create_missing_directories_of_file(directory)  # Create all the previous directory.
            os.makedirs(directory)  # Make a new one.


def create_directories(path):
    """Create all directory of the path if necessary.

    The directories are created recursively.
    """
    if path == "":
        return  # Nothing to do any more.
    parent = os.path.dirname(path)
    # If parent does not exists create it
    if not os.path.exists(parent):
        create_directories(parent)  # Create all the previous directory.
    os.makedirs(path)  # Make a new directory
