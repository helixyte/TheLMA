


def initialize_data():
    from thelma.data import moleculetype, species

    data = dict(
        molecule_types=moleculetype.create_data(),
        species=species.create_data(),
        )

    return data
