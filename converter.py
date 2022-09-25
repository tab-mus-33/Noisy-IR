import argparse
import json
import os
import sys



# Code adapted from https://github.com/yasumori

TEMPLATE = """<DOC>
<DOCNO>{}</DOCNO>
{}
</DOC>"""

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('file_list')
    parser.add_argument('out_dir')
    return parser.parse_args()

class Segmenter:
    def __init__(self, ranges, items):
        self.ranges = ranges
        self.segment_dict = self.create_segment_dict(ranges)

        self.active = []
        self.items = items

    def create_segment_dict(self, ranges):
        d = {}
        for s_time, e_time in ranges:
            d['{}-{}'.format(s_time, e_time)] = []
        return d

    def get_segment_dict(self):
        return self.segment_dict

    def run(self):
        self.active.append(self.ranges.pop())
        for item in self.items:
            start_time = float(item['startTime'].strip('s'))
            end_time = float(item['endTime'].strip('s'))

            if self.ranges:
                self.update_active(start_time, end_time)
            if self.active:
                self.update_complete(start_time, end_time)

            for active_range in self.active:
                key = '{}-{}'.format(*active_range)
                self.segment_dict[key].append(item['word'])

    def update_active(self, start_time, end_time):
        next_range = self.ranges[-1]
        if start_time >= next_range[0] and end_time < next_range[1]:
            self.active.append(self.ranges.pop())
        elif start_time <= next_range[0] and end_time > next_range[0]:
            self.active.append(self.ranges.pop())

    def update_complete(self, start_time, end_time):
        update = []
        for r in self.active:
            if end_time > r[1]:
                continue
            else:
                update.append(r)
        self.active = update

def extract_words(f_path):
    # there should be two transcripts for each json file
    # the 2nd transcripts contain speaker tag
    data = []
    with open(f_path) as ifile:
        json_out = json.load(ifile)
    transcripts = []
    cur_time = 0
    for res in json_out['results']:
        hyp = res['alternatives'][0]
        if not hyp:
            continue
        items = hyp['words']
        for item in items:
            end_time = float(item['endTime'].strip('s'))
            if end_time < cur_time:
                # when 1st transcripts is done, load 2nd ones
                data.append(transcripts)
                transcripts = []
            cur_time = end_time
            transcripts.append(item)
    if transcripts:
        data.append(transcripts)
    return data

def get_ranges(last_item):
    end_time = int(float(last_item['endTime'].strip('s')))
    # offsets in output need to be multiples of 60
    ranges = list(range(0, end_time, 60))
    segment_ranges = [(t, t+120) for t in ranges]
    segment_ranges.reverse()
    return segment_ranges

def extract_content(f_path):
    data = extract_words(f_path)
    if len(data) >= 3:
        print('{}: more than 3 transcription variants'.format(f_path),
                file=sys.stderr)
    # ignore the 2nd transcripts variant which contains SpeakerTag
    transcripts = data[0]
    segment_ranges = get_ranges(transcripts[-1])

    segmenter = Segmenter(segment_ranges, transcripts)
    segmenter.run()
    return segmenter.get_segment_dict()

def write_output(show_id, segment_dict, out_dir):
    with open(os.path.join(out_dir, show_id+'.xml'), 'w') as ofile:
        for k in sorted(list(segment_dict.keys())):
            # Add show_id and time stamps for identifier
            doc_no = '{}_{}'.format(show_id, k)

            print(' '.join(segment_dict[k]))

            
            to_write = TEMPLATE.format(
                    doc_no, ' '.join(segment_dict[k]))
            print(to_write, file=ofile)


if __name__=="__main__":
    #Change directory name here to read files 
    name_dir="content/drive/MyDrive/IRDM/JSON Files/6"
    for root, folder, data in os.walk(name_dir):
        if len(data)!=0:
            for i in data:
                print(os.path.join(root,i))
                segment_dict=extract_content(os.path.join(root,i))
                name=os.path.basename(os.path.join(root,i)).split('.')[0]
                # Change directory name here to write files 
                output_dir="/content/drive/MyDrive/IRDM/xml_dir/stemmer/"
                write_output(name, segment_dict, output_dir)
        
            