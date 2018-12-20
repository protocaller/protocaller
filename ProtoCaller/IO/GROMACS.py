import os as _os
import shutil as _shutil
import tempfile as _tempfile

import BioSimSpace as _BSS
import parmed as _pmd

import ProtoCaller.Utils.fileio as _fileio

def saveAsGromacs(filebase, system):
    name = _os.path.basename(_tempfile.TemporaryDirectory().name)
    with _fileio.Dir(dirname=name, temp=True) as dir:
        if "BioSimSpace" in str(type(system)):
            _BSS.IO.saveMolecules(filebase, system, "Gro87,GroTop")
            _pmd.load_file(filebase + ".gro87").save(filebase + ".gro")
            _shutil.move(filebase + ".gro", _os.path.join(dir.initialdirname, filebase + ".gro"))
            _shutil.move(filebase + ".grotop", _os.path.join(dir.initialdirname, filebase + ".top"))
        elif "GromacsTopologyFile" in str(type(system)) or "parmed" in str(type(system)):
            system.save(filebase + ".gro")
            system.save(filebase + ".top")
            _shutil.move(filebase + ".gro", _os.path.join(dir.initialdirname, filebase + ".gro"))
            _shutil.move(filebase + ".top", _os.path.join(dir.initialdirname, filebase + ".top"))
        else:
            raise TypeError("Passed object to save as GROMACS not recognised. Please pass BioSimSpace or ParmEd "
                            "objects only.")
    return [_os.path.abspath(filebase + ".gro"), _os.path.abspath(filebase + ".top")]