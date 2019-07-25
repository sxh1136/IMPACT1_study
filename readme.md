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
