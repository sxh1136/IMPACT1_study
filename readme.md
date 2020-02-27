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
Samples 13-6929545, 13-6929634 and 13-6929899 ommitted from further analysis as they contain very little data (<100,000 reads). 
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

# Phage Contig Identification
Predict genes with MetaGeneMark outputting genes in fasta format (-D) and gff (-f G):

```
for i in *.fasta; do prodigal -a ${i/contigs.fasta/prodigal.trans} -p meta -i ${i}; done
```

Filter out gene predictions that are smaller than 60 aa:

```
for i in *.trans; do bioawk -c fastx '{ if(length($seq) > 60) { print ">"$name; print $seq }}' ${i} > ${i/trans/filtered};done
```

Cluster genes using CD-HIT:
```
for i in *.filtered; do cd-hit -c 0.6 -aS 0.8 -g 1 -n 4 -d 0 -i ${i} -o ${i/prodigal.filtered/cd-hit}; done
```
Search for sequence homologs with HMMER
```
for i in *.cd-hit; do hmmsearch -E 0.001 -A ${i/cd-hit/hmmsearch.sto} /home/ubuntu/phageome/AllvogHMMprofiles/AllVOG.hmm ${i};done
```

# Phage Identification in metagenomic reads
Loop FastViromeExplorer for all paired end reads against the provided phage kallisto index (created from NCBI RefSeq) with a coverage cutoff of 40% (default 10%)
```
while read -A line; do java -cp bin FastViromeExplorer -1 /path_to_fastqs/${line[1]} -2 /path_to_fastqs/${line[2]} -i phage-kallisto-index-k31.idx -o /path_to_output/${line[1]/_1.fastq/_FVE} -co 0.4 ;done < fastq_list.txt
```
However this phage database is very limited containing only ~2000 genomes from refseq. We can instead use a database curated by Andrew Millard - http://millardlab.org/bioinformatics/bacteriophage-genomes/. This database contains duplicated genomes so we use dedupe to remove any genomes with 100% identity to another.

```
dedupe.sh in=28Jan2020.fasta out=28Jan2020_deduped.fa ac=f
# If you want to remove deplicates with min identity of 95%
dedupe.sh in=28Jan2020.fasta out=28Jan2020_R95_deduped.fa minidentity=95
```
This can then be indexed by Kallisto and used for FVE like above
```
kallisto index -i millard-phage_index.idx -db 28Jan2020_deduped.fa
```
FVE returns a sorted tsv file for each read pair containing four columns. We can remove column 3 in the same command as this is empty. 
```
for i in *tsv; do awk -i inplace '{FS ="\t"} {OFS ="\t"} {print $1,$2,$4}' ${i};done
```
To get your sample per million scaling factor take your "number_of_reads.txt" file and divide the second column by 1,000,000.
```
awk -i inplace '{print $1,$2,$2/1000000}' number_of_reads.txt
```
Now you want to divide your estimated read counts in each tsv by the corresponding per million scaling factor. We can do this with this script:
```
cat number_of_reads.txt | while read eachline;
    #echo the line to see what I'm working with
    do echo $eachline;
	#name some variables from each column of each line
	sname=`echo $eachline| awk '{print $1}'`;
	div=`echo $eachline| awk '{print $3}'`;
	#echo my new variables to see that it worked
	echo $sname; echo $div;
	#cat each data-containing tsv and use awk to place the new column.
	#store result in a new tsv
	cat ${sname}_millard_FVE_sorted_abundance.tsv| awk -v div="$div" '{FS ="\t"} {OFS ="\t"} {print $1,$2,$3,$3/div}' > ${sname}_new.tsv;
    done
```
This returns us a new column that has the header "0". This will probably freak out some programs so we can replace it with "rpm". Note we make sure to only replace the first instance of "0". 
```
for i in *tsv; do sed -i -e '0,/0/ s/0/rpm/' ${i};done
```
Take your file containing all the IDs and genome lengths in your database. We will divide the genome lengths by 1000 to convert them into kilobase. 
```
awk -i inplace '{FS ="\t"} {OFS ="\t"} {print $1, $2/1000}' millard-phage-genome-size.txt
```
Pass the tsv file and genome length list to coverage.py to divide the rpm by the respective genome length to get rpkm
```
for i in *tsv;do ./coverage.py ${i} millard-phage-genome-size.txt > ${i/new.tsv/coverage.tsv};done
```
To replace #VirusIdentifier with Phage (as hashtags are awkward)
```
for i in *tsv;do sed -i -e 's/#VirusIdentifier/Phage/' ${i};done
```
Then extarct columns 1 and 5:
```
for i in *tsv;do awk '{FS ="\t"} {OFS ="\t"} {print $1,$5}' ${i} > ${i/.tsv/_only.tsv};done
```
Rename file names by Day in ICU and then replace rpkm in each file with Day in ICU so they can be merged in R on this basis.
```
while read -A line; do mv ${line[1]}_coverage_only.tsv ${line[2]}_coverage_only.tsv;done < sample_2_day.txt
for i in *only.tsv; do sed -i 's@rpkm@'${i/_coverage_only.tsv}'@g' ${i};done
```
