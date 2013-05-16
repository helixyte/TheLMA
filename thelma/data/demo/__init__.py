

def initialize_demo_data(data):
    from thelma.data.demo import organization, gene

    demo = dict(
        organizations=organization.create_demo(),
        genes=gene.create_demo(data['species'])
        )

    return demo
