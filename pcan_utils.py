from can.interfaces.pcan import PcanBus
import can


def channels_matching_device_number(device_number):
    matching_channels = []
    for config in can.detect_available_configs('pcan'):
        with PcanBus(channel=config['channel']) as bus:
            if bus.get_device_number() == device_number:
                matching_channels.append(config['channel'])
    return matching_channels


if __name__ == '__main__':
    print(channels_matching_device_number(15))

