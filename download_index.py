import edgar
import os
if __name__ == '__main__':
    print('Cleaning...')
    os.system('rm out/*')
    print('Downloading....')
    edgar.download_index('./out', 2015, skip_all_present_except_last=False)
    print('Formatting...')
    os.system('for file in out/*.tsv; do echo "" >> $file; done')
    print('Stitching...')
    os.system('cat out/*.tsv > out/master.tsv')
    print('Filtering...')
    os.system('cat out/master.tsv | grep -h "|4|" > out/out.tsv')
    print('Adding header...')
    os.system("{ echo 'ID|NAME|TYPE|DATE|TXT|INDEX'; cat out/out.tsv; } > out/out.csv")
    print('Removing...')
    os.system('rm out/*.tsv')