def split_into_parts(array, num_parts):
    part_size = len(array) // num_parts
    parts = [array[i * part_size: (i + 1) * part_size] for i in range(num_parts)]
    parts[-1].extend(array[num_parts * part_size:])

    return parts

def find_differences(array1, array2):
    cpfs_array1 = set(obj['cpf'] for obj in array1)
    cpfs_array2 = set(obj['document'] for obj in array2)

    difference = cpfs_array1 - cpfs_array2

    array3 = [{'cpf': cpf} for cpf in difference]
    
    return array3