import pytest
from backend.parser.pdb_parser import parse_pdb

DUMMY_PDB = b"""
ATOM      1  N   MET A   1      27.340  24.430   2.614  1.00  9.67           N  
ATOM      2  CA  MET A   1      26.266  25.413   2.842  1.00 10.38           C  
ATOM      3  C   MET A   1      26.913  26.639   3.531  1.00  9.62           C  
ATOM      4  O   MET A   1      27.886  26.463   4.263  1.00  9.62           O  
ATOM      5  CB  MET A   1      25.112  24.880   3.649  1.00 13.77           C  
ATOM      6  CG  MET A   1      25.353  24.860   5.134  1.00 16.29           C  
ATOM      7  SD  MET A   1      23.930  23.959   5.904  1.00 17.17           S  
ATOM      8  CE  MET A   1      24.447  23.984   7.620  1.00 16.11           C  
ATOM      9  N   GLN A   2      26.335  27.770   3.258  1.00  9.27           N  
ATOM     10  CA  GLN A   2      26.850  29.021   3.898  1.00  9.07           C  
ATOM     11  C   GLN A   2      26.100  29.253   5.202  1.00  8.72           C  
ATOM     12  O   GLN A   2      24.865  29.024   5.330  1.00  8.22           O  
ATOM     13  CB  GLN A   2      26.733  30.148   2.905  1.00 14.46           C  
ATOM     14  CG  GLN A   2      27.150  31.485   3.409  1.00 17.01           C  
ATOM     15  CD  GLN A   2      28.496  31.766   2.730  1.00 24.08           C  
ATOM     16  OE1 GLN A   2      29.499  31.066   2.890  1.00 25.10           O  
ATOM     17  NE2 GLN A   2      28.530  32.836   1.979  1.00 24.31           N  
"""

def generate_dummy(n_residues=10):
    lines = []
    for i in range(1, n_residues + 1):
        lines.append(f"ATOM {i*4-3:6d}  N   ALA A {i:3d}      0.000   0.000   {i*3.8:.3f}  1.00  0.00           N  ")
        lines.append(f"ATOM {i*4-2:6d}  CA  ALA A {i:3d}      1.000   0.000   {i*3.8+1.0:.3f}  1.00  0.00           C  ")
        lines.append(f"ATOM {i*4-1:6d}  C   ALA A {i:3d}      2.000   0.000   {i*3.8+2.0:.3f}  1.00  0.00           C  ")
        lines.append(f"ATOM {i*4:6d}  O   ALA A {i:3d}      2.000   1.000   {i*3.8+2.5:.3f}  1.00  0.00           O  ")
    return "\n".join(lines).encode('utf-8')

def test_too_few_residues():
    with pytest.raises(ValueError, match="Minimum is 10"):
        parse_pdb(DUMMY_PDB)

def test_parse_success():
    pdb = generate_dummy(15)
    graph = parse_pdb(pdb)
    assert graph.n_residues == 15
    assert graph.ca_coords.shape == (15, 3)
    assert graph.cb_coords.shape == (15, 3)
    assert graph.distance_matrix.shape == (15, 15)
    # k-NN graph with k=10
    assert graph.edge_index.shape[1] == 15 * 10
    
def test_missing_ca():
    # If missing CA, BioPython parser gracefully handles it by ignoring the residue 
    # since we check if 'CA' in residue. Let's provide a PDB where one residue is missing CA.
    # It should just have n-1 residues.
    pdb = generate_dummy(15)
    # replace CA with CX in residue 5
    pdb = pdb.replace(b"CA  ALA A   5", b"CX  ALA A   5")
    graph = parse_pdb(pdb)
    assert graph.n_residues == 14
