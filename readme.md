# Downloading sequencing data from ENA
Study: PRJNA533528

Retrieve download info from ascension:
```
$ curl -X POST --header 'Content-Type: application/x-www-form-urlencoded' --header 'Accept: text/plain' -d 'result=read_run&query=study_accession%3DPRJNA533528&fields=fastq_ftp' 'https://www.ebi.ac.uk/ena/portal/api/search' > raw_data/fastq_info.txt
```

There are 2 links back to back in the line, so the script will try and read them both as one link unless you put the space in between them and make them two separate columns. To separate the links replace the semicolon with a tab using:
```
$ sed 's/;/\t/'g fastq_info.txt > fastq_locations.txt
```

Now download the fastq files using the locations file using wget:
```
$ while read -A line ; do wget ${line[2]} ; wget ${line[3]} ; done < fastq_locations.txt
```

As the fastq files are named according to their ENA sample accession, they need to be renamed. The file SampleID_to_run-accession.txt is a tsv file containing the sample accessions and their corresponding sample IDs. A while loop is used to do this:
```
$ while read -A line; do mv ${line[1]} ${line[2]}; done < SampleID_to_run-accession.txt
``` 

There are also three missing fastq files on ENA, as well as one that was uploaded incorrectly (13-6929666) that can be downloaded from [here](https://www.dropbox.com/sh/tzgwrdf571k3p5s/AADxy8aVGLEF_ZavbUiW9SCya?dl=0)
 
# Quality Control
Samples 13-6929545, 13-6929633, 13-6929634 and 13-6929899 ommitted from further analysis as they contain very little data (<100,000 reads). 
### Unzipping fastq files
First of all, we need to decompress our fastq files using gzip. Using the GNU parallel command will decompress multiple files at once (according to how many cores we have).
```
$ ls *.gz | parallel gunzip
``` 

### Fastqc
Run Fastqc on all samples in parallel
```
$ for i in *.fastq; do echo "${i}"; done | parallel fastqc -o fastqc
```

### Remove exact duplicates
Although not strictly necessary, as our duplicate levels are quite high it is desirable to remove exact duplicates to lessen downstream computational load. We can do this with the -derep 1 flag in prinseq-lite.

```
$ for i in *_1.fastq; do prinseq-lite.pl -fastq ${i} -fastq2 ${i/_1.fastq/_2.fastq} -out_format 3 -derep 1 -out_bad null; done
```

```
$ for i in *.fastq; do mv ${i} ${i/prinseq*fastq/clean.fastq}; done
```

# Metagenome Assembly
### IDBA
~~Before using IDBA_UD for sequences longer than 100bp you need to increase the kMaxShortSequence value in src/sequence/shortsequence.h. This needs to be done before compiling the software.~~

~~IDBA_UD also requires paired reads to be in a single merged fasta format. They provide a fq2fa script for this:~~

~~for i in *_1_clean.fastq; do fq2fa --merge --filter ${i} ${i/_1_clean.fastq/_2_clean.fastq} ${i/_1_clean.fastq/_merged.fasta};done~~  

~~To run the assembler with default parameters:~~

~~for  i in *fasta; do idba_ud -r ${i} -o ${i/merged.fasta/idba_ud} --num_threads 8;done~~


~~IDBA is poorly documented and insert size error could not be solved.~~

### metaSPAdes
Instead samples will be assembled with metaSPAdes instead

```
for i in *1_clean.fastq; do /home/linuxbrew/.linuxbrew/bin/spades.py --meta -o ${i/1_clean.fastq/metaspades} -1 ${i} -2 ${i/_1_clean.fastq/_2_clean.fastq}; done
```

### metaphlan
Run metaphlan to get non-viral abundance estimates. (Running with add-viruses didn't really change the results. Metaphlan not great at detecting viruses). 
```
# Run metaphlan
for i in *_1_*gz;do echo "metaphlan ${i},${i/_1_/_2_} --bowtie2out ${i/_1_clean.fastq.gz/_bowtie2out} --nproc 16 --input_type fastq --unclassified_estimation -o ${i/_1_clean.fastq.gz/_metaphlan.txt}";done
# Move metaphlan output into patient specific directories
for i in patient*txt; do while read -A line; do cp ${line}_metaphlan.txt ${i/.txt/};done < ${i};done
# Merge metaphlan tables for each patient
for i in patient_*;do merge_metaphlan_tables.py ${i}/*metaphlan.txt > ${i}_metaphlan.txt;done
# Extract species lines for merged metaphlan tables
for i in *metaphlan.txt; do awk 'NR==2' ${i} > ${i/metaphlan/metaphlan_species}; grep -E "(s__)|(^ID)" ${i} | grep -v "t__" | sed 's/^.*s__//g' >> ${i/metaphlan/metaphlan_species};done
# Remove metaphlan tag
for i in *species*; do sed -i 's/_metaphlan//g' ${i};done
# Replace sample IDs with days in ICU
for i in *species.txt; do awk 'NR == FNR {T[$1] = $3; next} {for (t in T) gsub (t, T[t])} 1' sample-id_to_day.txt ${i} > ${i/.txt/_dayICU.txt};done
```

