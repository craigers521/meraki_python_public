from meraki import meraki
import logging
import time

api_key = '##############'
org_id = '############'

logging.basicConfig(filename='tag_test.log')

networks = meraki.getnetworklist(api_key, org_id)
input_file = open('test.csv')
line_num = 0

for line in input_file:
    line_num += 1
    inputs = line.split(',')
    #print(inputs)
    try:
        new_tags = [inputs[1], inputs[2], inputs[3], inputs[4], inputs[5]]
    except IndexError:
        logging.error("Line # {} is not correct".format(line_num))
    print("updating {}".format(inputs[0]))
    try:
        current_site = next(network for network in networks if network['name'] == inputs[0])
        result = meraki.updatenetwork(api_key, current_site['id'], name='', tz='', tags=new_tags)
        time.sleep(0.5)
    except (StopIteration, TypeError):
        logging.error("network {} not found".format(inputs[0]))
