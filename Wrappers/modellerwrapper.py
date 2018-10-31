'''TO DO:
1. Deal with ending loop residues - e.g. add option to ignore them
2. See how modified protein residues are affected
3. Renumber residues - sometimes PDB files provide negative numbers - might crash other pieces of software
4. Still haven't implemented addition of missing atoms'''

import copy as _copy
import re as _re

import modeller as _modeller
import modeller.automodel as _modellerautomodel

import IO as _IO

#taken from https://salilab.org/modeller/manual/node36.html
class MyLoop(_modellerautomodel.loopmodel):
    def __init__(self, filename=None, *args, **kwargs):
        super(MyLoop, self).__init__(*args, **kwargs)
        if(filename is not None):
            self.pdb = _IO.PDB.PDB(filename)
            self.total_residue_list = self.pdb.totalResidueList()
            self.transformed_total_residue_list = self._transform_id(self.total_residue_list)
            self.missing_residue_list = [res for res in self.total_residue_list if type(res) == _IO.MissingResidue]
            self.transformed_missing_residue_list = [self.transformed_total_residue_list[i]
                                                     for i, res in enumerate(self.total_residue_list)
                                                     if type(res) == _IO.PDB.MissingResidue]
        else:
            raise ValueError("Need to specify input PDB filename")

        self.selection = _modeller.selection()

    def select_loop_atoms(self):
        for residue in self.transformed_missing_residue_list:
            try:
                self.selection.add(self.residues[residue])
            except KeyError:
                try:
                    self.selection.add(self.residues[residue[:-2]])
                except KeyError:
                    print("Error while selecting missing residue: %s. "
                          "Residue either missing from FASTA sequence or there is a problem with Modeller." % residue)
        return self.selection

    def _transform_id(self, reslist):
        modified_id_list = []
        for i, res in enumerate(reslist):
            modified_id_list += ["{}:{}".format(i + 1, res._chainID)]
        return modified_id_list

def modellerTransform(filename_pdb, filename_fasta):
    env = _modeller.environ()
    pdb_code = filename_pdb[:4]

    #convert FASTA to PIR
    filename_pir = FASTA2PIR(filename_fasta)

    m = MyLoop(env=env,
               alnfile=filename_pir,
               knowns=("PROT"),
               filename=filename_pdb,
               #inimodel=filename_pdb,  # initial model of the target
               sequence=pdb_code.upper(),  # code of the target
               loop_assess_methods=_modeller.automodel.assess.DOPE)

    m.auto_align()  # get an automatic alignment
    m.make()

    return fixModellerPDB(m, filename_output=pdb_code + "_modeller.pdb")

def FASTA2PIR(filename_input):
    file = open(filename_input).readlines()
    pdb_code = ""
    new_file = []

    for line in file:
        if not pdb_code:
            match = _re.search(r">([\w]{4})", line)
            if(match):
                pdb_code = match.group(1)
            new_file = [">P1;%s\nsequence:::::::::\n" % pdb_code]
        else:
            if(_re.search(r">[\w]{4}", line)):
                new_file += "/"
            else:
                new_file += line

    filename_output = pdb_code + ".pir"
    with open(filename_output, "w") as file:
        file.write(">P1;PROT\nstructureX:%s:FIRST:@ END::::::\n*\n\n" % pdb_code)
        for i, line in enumerate(new_file):
            if(i != len(new_file) - 1): file.write(line)
            else: file.write(line[:-1])
        file.write("*")

    return filename_output

def fixModellerPDB(model, filename_output=None):
    def getAndFixResidue(index, missing_residue):
        nonlocal pdb_modified
        modified_residue = _copy.deepcopy(pdb_modified.filterResidues(includedict={"_resSeq": [index]})[0])
        modified_residue._chainID = missing_residue._chainID
        modified_residue._resSeq = missing_residue._resSeq
        modified_residue._iCode = missing_residue._iCode
        return modified_residue

    def equalChainIDs(res_orig, res_mod):
        if (res_orig == "A" and res_mod == " ") or res_orig == res_mod:
            return True
        else:
            return False

    try:
        filename_modified = model.loop.outputs[0]['name']
    except:
        print("Modeller failed to create file. Please see log.")
        return -1

    pdb_modified = _IO.PDB.PDB(filename_modified)
    for missing_residue in model.missing_residue_list:
        index = 1
        breakloops = False
        for i, chain in enumerate(model.pdb):
            if chain._type == "chain":
                for j, residue in enumerate(chain):
                    if j == 0 and equalChainIDs(missing_residue, residue) and missing_residue < residue:
                        chain.insertResidue(j, getAndFixResidue(index, missing_residue))
                        breakloops = True
                    elif j == len(chain) - 1 and equalChainIDs(missing_residue, residue) and residue < missing_residue:
                        chain.insertResidue(j + 1, getAndFixResidue(index, missing_residue))
                        breakloops = True
                    elif 0 < j < len(chain) and chain[j - 1] < missing_residue < chain[j]:
                        chain.insertResidue(j, getAndFixResidue(index, missing_residue))
                        breakloops = True
                    if residue._type == "amino acid":
                        index += 1
                    if breakloops:
                        break
            if breakloops:
                break

    model.pdb.reNumberAtoms()
    if (filename_output == None):
        filename_output = model.pdb.filename[:-4] + "_modified.pdb"
    model.pdb.writePDB(filename_output)
    return filename_output