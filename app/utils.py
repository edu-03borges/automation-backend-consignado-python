def split_into_parts(array, num_parts):
    part_size = len(array) // num_parts
    parts = [array[i * part_size: (i + 1) * part_size] for i in range(num_parts)]
    parts[-1].extend(array[num_parts * part_size:])

    return parts