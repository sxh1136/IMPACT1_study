#!/usr/bin/env python3
import sys

counts_fname = sys.argv[1]
genome_lengths_fname = sys.argv[2]

genome_length_dict = {}
with open(genome_lengths_fname) as genome_lengths_f:
    # Checking the header line, for extra safety
    header = genome_lengths_f.readline().strip().split("\t")
    assert header[0] == "ID"
    assert header[1] == "length"
    # Reading the data lines
    for line in genome_lengths_f:
        [virus_identifier, genome_length] = line.strip().split("\t")
        genome_length_dict[virus_identifier] = int(genome_length)

with open(counts_fname) as counts_f:
    print("#VirusIdentifier\tVirusName\tspecies\tEstimatedAbundance\tbp\tbp/length")
    # Checking the header line, for extra safety
    header = counts_f.readline().strip().split("\t")
    assert header[0] == "#VirusIdentifier"
    assert header[1] == "VirusName"
    assert header[2] == "species"
    assert header[3] == "EstimatedAbundance"
    assert header[4] == "bp"
    # Reading the data lines
    for line in counts_f:
        [virus_identifier, VirusName, species, Estimated_abundance, counts] = line.strip().split("\t")
        # /!\ It would be different in python 2:
        # different print and division behaviours
        print(
            virus_identifier, VirusName, species, float(counts),
            float(counts) / genome_length_dict[virus_identifier],
            sep="\t")

sys.exit(0)
