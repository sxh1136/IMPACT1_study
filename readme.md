# Downloading sequencing data from ENA
Study: PRJNA533528

Retrieve download info from ascension:
```
curl -X POST --header 'Content-Type: application/x-www-form-urlencoded' --header 'Accept: text/plain' -d 'result=read_run&query=study_accession%3DPRJNA533528&fields=fastq_ftp' 'https://www.ebi.ac.uk/ena/portal/api/search' > raw_data/fastq_info.txt
```

There are 2 links back to back in the line, so the script will try and read them both as one link unless you put the space in between them and make them two separate columns. To separate the links replace the semicolon with a tab using:
```
sed 's/;/\t/'g fastq_info.txt > fastq_locations.txt
```

Now download the fastq files using the locations file using wget:
```
while read -A line ; do wget ${line[2]} ; wget ${line[3]} ; done < fastq_locations.txt
```

As the fastq files are named according to their ENA sample accession, they need to be renamed. The file SampleID_to_run-accession.txt is a tsv file containing the sample accessions and their corresponding sample IDs. A while loop is used to do this:
```
while read -A line; do mv ${line[1]} ${line[2]}; done < SampleID_to_run-accession.txt
``` 

There are also three missing fastq files on ENA, as well as one that was uploaded incorrectly (13-6929666) that can be downloaded from [here](https://www.dropbox.com/sh/tzgwrdf571k3p5s/AADxy8aVGLEF_ZavbUiW9SCya?dl=0)
 
# Quality Control
### Unzipping fastq files
First of all, we need to decompress our fastq files using gzip. Using the GNU parallel command will decompress multiple files at once (according to how many cores we have).
```
ls *.gz | parallel gunzip
``` 

### Fastqc
Run Fastqc on all samples in parallel
```
for i in *.fastq; do echo "${i}"; done | parallel fastqc -o fastqc
```
