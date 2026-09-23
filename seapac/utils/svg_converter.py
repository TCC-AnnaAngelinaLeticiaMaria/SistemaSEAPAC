import vtracer

def converter_svg(img):
    img.seek(0)

    dados = img.read()
    nome = img.name.lower()

    if nome.endswith('.jpg') or nome.endswith('.jpeg'):
        formato = 'jpg'
    elif nome.endswith('.png'):
        formato = 'png'
    elif nome.endswith('.webp'):
        formato = 'webp'
    else:
        raise ValueError("Formato de imagem inválido!")

    svg = vtracer.convert_raw_image_to_svg(
        dados,
        img_format=formato,
        colormode='color',
        hierarchical='stacked',
        mode='spline',
        filter_speckle=8,
        color_precision=6,
        layer_difference=18,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=3
    )

    return svg