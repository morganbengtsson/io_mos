import bpy
import bmesh
import struct
import json
import os


def uv_from_vert_first(uv_layer, v):
    for l in v.link_loops:
        uv_data = l[uv_layer]
        return uv_data.uv
    return None


def has_material_index(vertex, index):
    has_index = False
    for face in vertex.link_faces:
        if face.material_index == index:
            has_index = True
            return has_index
    return has_index


def round_3d(v):
    return round(v[0], 6), round(v[1], 6), round(v[2], 6)


def round_2d(v):
    return round(v[0], 6), round(v[1], 6)


def mesh_path(blender_object):
    name = blender_object.data.name
    if len(blender_object.modifiers) > 0:
        name = blender_object.name
    for modifier in blender_object.modifiers:
        name += "_" + modifier.name.lower()

    library = os.path.splitext(bpy.path.basename(bpy.context.blend_data.filepath))[0] + '/'
    if blender_object.data.library:
        library, file_extension = os.path.splitext(bpy.path.basename(blender_object.data.library.filepath))
        library = library + '/'
    path = library + "meshes/" + name + ".mesh"
    return path.strip('/')


def write_mesh_file(report, blender_object, write_dir):
    try:
        mesh = blender_object.to_mesh(depsgraph=bpy.context.depsgraph,
                                      apply_modifiers=True)

    except Exception as exception:
        print("Error in object " + blender_object.name)
        raise exception

    filepath = write_dir + '/' + mesh_path(blender_object)

    positions = []
    normals = []
    tangents = []
    texture_uvs = []
    weights = []

    faces = []
    vertex_dict = {}
    vertex_count = 0

    if len(mesh.uv_layers) >= 1:
        mesh.calc_loop_triangles()
        for i, tri in enumerate(mesh.loop_triangles):
            temp_faces = []
            for j, vertex_index in enumerate(tri.vertices):
                position = round_3d(mesh.vertices[vertex_index].co.to_tuple())
                if tri.use_smooth:
                    normal = round_3d(mesh.vertices[vertex_index].normal)
                else:
                    normal = round_3d(tri.normal.to_tuple())

                loop_index = tri.loops[j]
                texture_uv = list(round_2d(mesh.uv_layers[0].data[loop_index].uv))

                texture_uv[1] = 1.0 - texture_uv[1]
                texture_uv = tuple(texture_uv)
                weight = mesh.vertices[vertex_index].bevel_weight

                key = mesh.vertices[vertex_index].index
                vertex_index = vertex_dict.get(key)

                if tri.use_smooth:
                    if vertex_index is None:  # vertex not found
                        vertex_dict[key] = vertex_count
                        positions.append(position)
                        normals.append(normal)
                        texture_uvs.append(texture_uv)
                        temp_faces.append(vertex_count)
                        tangents.append((0.0, 0.0, 0.0))
                        weights.append(weight)
                        vertex_count += 1
                    else:
                        inx = vertex_dict[key]
                        temp_faces.append(inx)
                else:
                    positions.append(position)
                    normals.append(normal)
                    texture_uvs.append(texture_uv)
                    temp_faces.append(vertex_count)
                    tangents.append((0.0, 0.0, 0.0))
                    weights.append(weight)
                    vertex_count += 1

            if len(temp_faces) == 3:
                faces.append(temp_faces)
            else:
                faces.append([temp_faces[0], temp_faces[1], temp_faces[2]])
                faces.append([temp_faces[0], temp_faces[2], temp_faces[3]])

        indices = [val for sublist in faces for val in sublist]
    else:
        raise Exception(mesh.name + " must have one uv layer")

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    mesh_file = open(filepath, 'bw')

    # Header
    mesh_file.write(struct.pack('i', len(positions)))
    mesh_file.write(struct.pack('i', len(indices)))

    # Body
    for vertex_index in zip(positions, normals, tangents, texture_uvs, weights):
        mesh_file.write(struct.pack('fff', *vertex_index[0]))
        mesh_file.write(struct.pack('fff', *vertex_index[1]))
        mesh_file.write(struct.pack('fff', *vertex_index[2]))
        mesh_file.write(struct.pack('ff', *vertex_index[3]))
        mesh_file.write(struct.pack('f', vertex_index[4]))

    for i in indices:
        mesh_file.write(struct.pack('I', i))

    mesh_file.close()
    report({'INFO'}, "Wrote: " + filepath)


def write(report, write_dir, objects):
    objects = [o for o in objects if o.type == 'MESH']

    for blender_object in objects:
        write_mesh_file(report, blender_object, write_dir)
    report({'INFO'}, "Wrote all meshes.")
