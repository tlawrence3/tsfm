import pytest
import os

@pytest.fixture(scope="module")
def cove_files(tmpdir_factory):
    struct_string_cove = "#=CS	>>>>>>>..>>>>...........<<<<.>>>>>.......<<<<<.....>>>>>....\n#=CS	...<<<<<<<<<<<<.\n"
    struct_string_text ="""A:0,72,1,71,2,70,3,69,4,68,5,67,6,66
D:9,25,10,24,11,23,12,22
C:27,43,28,42,29,41,30,40,31,39
T:49,65,50,64,51,63,52,62,53,61
"""
    H_class = """CLUSTAL W (1.81) multiple sequence alignment


HGTG_gi|1002161287|ref|NC_029347.1||109108|109035|0|0|tSE|-||GNET| GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
HGTG_gi|1002161287|ref|NC_029347.1||61258|61331|0|0|tSE|+||GNET|   GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
HGTG_gi|187763084|ref|NC_010654.1||118994|118921|0|0|tSE|-||GNET|  GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGGATCCACCACgCGCGGGTTCA
HGTG_gi|187763084|ref|NC_010654.1||69289|69362|0|0|tSE|+||GNET|    GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGGATCCACCACgCGCGGGTTCA
HGTG_gi|222084134|ref|NC_011942.1||56864|56791|0|0|tSE|-||GNET|    GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
HGTG_gi|222084134|ref|NC_011942.1||9716|9789|0|0|tSE|+||GNET|      GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
HGTG_gi|222139869|ref|NC_011954.1||109042|108969|0|0|tSE|-||GNET|  GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
HGTG_gi|222139869|ref|NC_011954.1||61119|61192|0|0|tSE|+||GNET|    GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
HGTG_gi|512721557|ref|NC_021438.1||114464|114391|0|0|tSE|-||GNET|  GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
HGTG_gi|512721557|ref|NC_021438.1||67253|67326|0|0|tSE|+||GNET|    GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
HGTG_gi|752789973|ref|NC_026301.1||114178|114105|0|0|tSE|-||GNET|  GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
HGTG_gi|752789973|ref|NC_026301.1||67436|67509|0|0|tSE|+||GNET|    GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
HGTG_gi|966203074|ref|NC_028734.1||56111|56038|0|0|tSE|-||GNET|    GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
HGTG_gi|966203074|ref|NC_028734.1||9449|9522|0|0|tSE|+||GNET|      GCGGACGTAGCCAAGT--GGCtcAAGGCAGTGGATTGTGAATCCACCACgCGCGGGTTCA
                                                                   ****************  ********************* ********************


HGTG_gi|1002161287|ref|NC_029347.1||109108|109035|0|0|tSE|-||GNET| ATCCCCGTCGTTCGCC
HGTG_gi|1002161287|ref|NC_029347.1||61258|61331|0|0|tSE|+||GNET|   ATCCCCGTCGTTCGCC
HGTG_gi|187763084|ref|NC_010654.1||118994|118921|0|0|tSE|-||GNET|  ATCCCCGTCGTTCGCC
HGTG_gi|187763084|ref|NC_010654.1||69289|69362|0|0|tSE|+||GNET|    ATCCCCGTCGTTCGCC
HGTG_gi|222084134|ref|NC_011942.1||56864|56791|0|0|tSE|-||GNET|    ATCCCCGTCGTTCGCC
HGTG_gi|222084134|ref|NC_011942.1||9716|9789|0|0|tSE|+||GNET|      ATCCCCGTCGTTCGCC
HGTG_gi|222139869|ref|NC_011954.1||109042|108969|0|0|tSE|-||GNET|  ATCCCCGTCGTTCGCC
HGTG_gi|222139869|ref|NC_011954.1||61119|61192|0|0|tSE|+||GNET|    ATCCCCGTCGTTCGCC
HGTG_gi|512721557|ref|NC_021438.1||114464|114391|0|0|tSE|-||GNET|  ATCCCCGTCGTTCGCC
HGTG_gi|512721557|ref|NC_021438.1||67253|67326|0|0|tSE|+||GNET|    ATCCCCGTCGTTCGCC
HGTG_gi|752789973|ref|NC_026301.1||114178|114105|0|0|tSE|-||GNET|  ATCCCCGTCGTTCGCC
HGTG_gi|752789973|ref|NC_026301.1||67436|67509|0|0|tSE|+||GNET|    ATCCCCGTCGTTCGCC
HGTG_gi|966203074|ref|NC_028734.1||56111|56038|0|0|tSE|-||GNET|    ATCCCCGTCGTTCGCC
HGTG_gi|966203074|ref|NC_028734.1||9449|9522|0|0|tSE|+||GNET|      ATCCCCGTCGTTCGCC
                                                                   ****************
"""
    K_class = """CLUSTAL W (1.81) multiple sequence alignment


Kttt_gi|1002161287|ref|NC_029347.1||3573|1209|38|2330|ARA|-||GNET| GGGTTGCTAACTCAAT--GGT--AGAGTACTCGGCTTTTAACCGACTAGtTCCGGGTTCG
Kttt_gi|187763084|ref|NC_010654.1||3659|1145|38|2480|ARA|-||GNET|  GGGTTGCTAACTCAAT--GGT--AGAGTACTCGGCTTTTAACCGAAGAGtTCCGGGTTCG
Kttt_gi|222084134|ref|NC_011942.1||5508|7908|38|2366|ARA|+||GNET|  GGGTTGCTAACTCAAT--GGT--AGAGTACTCGGCTTTTAACCGAAGAGtTCCGGGTTCG
Kttt_gi|222139869|ref|NC_011954.1||3577|1209|38|2334|ARA|-||GNET|  GGGTTGCTAACTCAAT--GGT--AGAGTACTCGGCTTTTAACCGACTAGtTCCGGGTTCG
Kttt_gi|512721557|ref|NC_021438.1||3654|1253|38|2367|ARA|-||GNET|  GGGTTGCTAACTCAAT--GGT--AGAGTACTCGGCTTTTAACCGAAGAGtTCCGGGTTCG
Kttt_gi|752789973|ref|NC_026301.1||3353|968|38|2351|ARA|-||GNET|   GGGTTGCTAACTCAAT--GGT--AGAGTACTCGGCTTTTAACCGAAGAGtTCCGGGTTCG
Kttt_gi|966203074|ref|NC_028734.1||5248|7641|38|2359|ARA|+||GNET|  GGGTTGCTAACTCAAT--GGT--AGAGTACTCGGCTTTTAACCGAAGAGtTCCGGGTTCG
                                                                   ****************  ***  **********************  *************


Kttt_gi|1002161287|ref|NC_029347.1||3573|1209|38|2330|ARA|-||GNET| AATCCCGGGCAACCCA
Kttt_gi|187763084|ref|NC_010654.1||3659|1145|38|2480|ARA|-||GNET|  AATCCCGGGCAACCCA
Kttt_gi|222084134|ref|NC_011942.1||5508|7908|38|2366|ARA|+||GNET|  AATCCCGGGCAACCCA
Kttt_gi|222139869|ref|NC_011954.1||3577|1209|38|2334|ARA|-||GNET|  AATCCCGGGCAACCCA
Kttt_gi|512721557|ref|NC_021438.1||3654|1253|38|2367|ARA|-||GNET|  AATCCCGGGCAACCCA
Kttt_gi|752789973|ref|NC_026301.1||3353|968|38|2351|ARA|-||GNET|   AATCCCGGGCAACCCA
Kttt_gi|966203074|ref|NC_028734.1||5248|7641|38|2359|ARA|+||GNET|  AATCCCGGGCAACCCA
                                                                   ****************

"""
    cove = tmpdir_factory.mktemp("data").join("struct_cove.txt")
    cove.write(struct_string_cove)
    cove_file = open(str(cove), "r")
    text = tmpdir_factory.mktemp("data").join("struct_text.txt")
    text.write(struct_string_text)
    text_file = open(str(text), "r")
    H_file = tmpdir_factory.mktemp("data").join("GNET_H.aln")
    H_file.write(H_class)
    K_file = open(str(H_file)[:-10] + "GNET_K.aln", "w")
    K_file.write(K_class)
    K_file.close()
    return ({'cove': cove_file, 'prefix': str(H_file)[:-6], 'tmp': str(H_file)[:-10], 'text': text_file})

