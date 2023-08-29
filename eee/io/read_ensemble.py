import eee

import json
import os
import inspect

def _search_for_key(some_dict,
                    search_key,
                    current_stack=None):
    """
    Recursively search a potentially nested dictionary for a specific key. 
    (Depth-first search.) Return the sequence of keys necessary to reach the 
    matched key. Does *not* check for duplicate keys; will return the key path
    to the first match it encounters. 
    """
    
    # Build current_stack for first iteration
    if current_stack is None:
        current_stack = []
    
    # Go through keys in dict
    for key in some_dict:
            
        # If we match the key, append to current_stack and return
        if key == search_key:
            current_stack.append(key)
            return current_stack
        
        # If we hit a nested dictionary, record the current key and search 
        # downstream for the search key. 
        if issubclass(type(some_dict[key]),dict):
            
            current_stack.append(key)
            current_stack = _search_for_key(some_dict=some_dict[key],
                                            search_key=search_key,
                                            current_stack=current_stack)
            
            # If we did not find the key, remove the key we used to access this
            # dictionary from the stack -- no match downstream. 
            if current_stack[-1] != search_key:
                current_stack = current_stack[:-1]
                
    return current_stack

def _spreadsheet_to_ensemble(df,gas_constant=None):
    """
    Load a spreadsheet and try to convert to an ensemble. Rows are treated as 
    different species; columns as keyword parameters (dG0, mu_stoich, etc.)
    """

    # Figure out gas constant (can't come from spreadsheet)
    if gas_constant is None:
        gas_constant = eee.Ensemble()._gas_constant

    # Create ensemble
    ens = eee.Ensemble(gas_constant=gas_constant)
    
    # Figure out the required and allowed keyword arguments to add_species. 
    required = []
    allowed = []
    allowed_args = inspect.signature(ens.add_species).parameters
    for k in allowed_args:
        if allowed_args[k].default is inspect._empty:
            required.append(k)
        else:
            allowed.append(k)
        
    required = set(required)
    allowed = set(allowed)

    print("Loading ensemble from a spreadsheet\n")

    # Read spreadsheet
    df = eee.io.read_dataframe(df)
        
    # Get columns from spreadsheet
    columns = set(df.columns)

    # Look for missing required arguments
    missing_required = required - columns
    if len(missing_required) > 0:
        err = "\nspreadsheet does not have all required columns.\n"
        err += "Missing columns are:\n"
        for m in missing_required:
            err += f"    {m}\n"
        raise ValueError(err)

    # Figure out which columns to send in as stoichiometries and which to send
    # in as keywords. 
    pass_as_mu = columns - allowed - required
    pass_as_kwargs = columns - pass_as_mu
    
    # Print kwarg status
    pass_as_kwargs = list(pass_as_kwargs)
    pass_as_kwargs.sort()
    for k in pass_as_kwargs:
        print(f"Interpreting column '{k}' as a ensemble.add_species keyword")

    # Print mu status
    pass_as_mu = list(pass_as_mu)
    pass_as_mu.sort()
    for m in pass_as_mu:
        print(f"Interpreting column '{m}' as a stoichiometry")

    # Now load each row in as a species. 
    for idx in df.index:

        # Construct kwargs
        kwargs = {}
        for k in pass_as_kwargs:
            kwargs[k] = df.loc[idx,k]
            
        # Construct mu_stoich
        mu_stoich = {}
        for m in pass_as_mu:
            mu_stoich[m] = df.loc[idx,m]
        kwargs["mu_stoich"] = mu_stoich
            
        # Add species
        ens.add_species(**kwargs)
    
    return ens


def _json_to_ensemble(json_file):

    # Read json file
    with open(json_file) as f:
        calc_input = json.load(f)
    
    # Look for "ens" key somewhere in the json output. If it's there, pull that
    # sub-dictionary out by itself
    key_stack = _search_for_key(calc_input,"ens")
    if len(key_stack) == 0:
        err = "\njson file does not have an 'ens' key\n\n"
        raise ValueError(err)
    
    for k in key_stack:
        calc_input = calc_input[k]
            
    # If specified, get gas constant out of dictionary
    if "gas_constant" in calc_input:
        gas_constant = calc_input.pop("gas_constant")
    else:
        # Get default from Ensemble class
        gas_constant = eee.Ensemble()._gas_constant

    # {"spreadsheet":some_file} case
    if "spreadsheet" in calc_input:
        return _spreadsheet_to_ensemble(df=calc_input["spreadsheet"],
                                        gas_constant=gas_constant)
    
    # Create ensemble from entries and validate. 
    ens = eee.Ensemble(gas_constant=gas_constant)
    for s in calc_input:
        try:
            ens.add_species(name=s,**calc_input[s])
        except TypeError:
            err = f"\nMangled json. Check ensemble keywords for species '{s}'\n\n"
            raise ValueError(err)

    return ens


def read_ensemble(input_file):
    """
    Read an ensemble from a file. The file can either be json file or a 
    spreadsheet (csv, tsv, xlsx). 

    Parameters
    ----------
    input_file : str
        input file to read

    Notes
    -----
    If a the input is json, the ensemble is defined under the "ens" key. There
    are several acceptable formats. The simplest just lists all species, where
    the name of the species is the key and the parameters are dictionary of
    values. Any keyword arguments to the :code:`Ensemble.add_species` method 
    that are not defined revert to the default value for that argument in 
    method. Some examples follow:

    ..code-block:: json

        {
          "ens":{
            "one":{"dG0":0,"mu_stoich":{"X":1},"observable":true,"folded":false},
            "two":{"dG0":0,"mu_stoich":{"Y":1},"observable":false,"folded":false},
          }
        }

    You can add the special key "gas_constant" to define the gas constant:

    ..code-block:: json

        {
          "ens":{
            "gas_constant":0.00197,
            "one":{"dG0":0,"mu_stoich":{"X":1},"observable":true,"folded":false},
            "two":{"dG0":0,"mu_stoich":{"Y":1},"observable":false,"folded":false},
          }
        }

    You can also use the special key "spreadsheet" to point to a spreadsheet
    file defining the ensemble. This key, if present, overrides all others. 

    ..code-block:: json

        {
          "ens":{
            "gas_constant":0.00197,
            "spreadsheet":"ensemble.xlsx"
          }
        }

    You can also embed an ensemble within more complicated json defining a 
    simulation using the "ens" key. eee will search for the "ens" key and, if
    present, build the ensemble from whatever is under that key. 

    ..code-block:: json

        {
            "calc_type":"wf_tree_sim",
            "calc_params":{
                "param_1":10,
                "param_2":0.01
            },
            "ens":{
                "gas_constant":0.00197,
                "one":{"dG0":0,"mu_stoich":{"X":1},"observable":true,"folded":false},
                "two":{"dG0":0,"mu_stoich":{"Y":1},"observable":false,"folded":false},
            }
        }

    When reading a spreadsheet, eee treats the rows as species and the columns
    as values. It looks for columns corresponding to the keyword arguments to 
    :code:`Ensemble.add_species` and uses those values when adding each row to 
    the ensemble. Omitted keywords use their default values from the method. 
    The :code:`mu_stoich` key should *not* be used. Instead, any columns in the
    spreadsheet that do not correspond to a keyword are treated as chemical 
    potential stoichiometries. The following spreadsheet defines two species, 
    s1 and s2. s1 interacts with molecule "X" with a stoichiometry of 1, s2 
    interacts with molecule "Y" with a stoichiometry of 2.

    +------+-----+------------+---+---+
    | name | dG0 | observable | X | Y | 
    +------+-----+------------+---+---+
    | s1   | 0   | TRUE       | 1 | 0 |
    +------+-----+------------+---+---+
    | s2   | 5   | FALSE      | 0 | 2 |
    +------+-----+------------+---+---+
    """

    input_file = f"{input_file}"
    if not os.path.isfile(input_file):
        err = "\ninput_file '{input_file}' is not a file\n\n"
        raise FileNotFoundError(err)

    # Parse as json or spreadsheet. 
    if input_file[-5:] == ".json":
        ens = _json_to_ensemble(input_file)
    else:
        ens = _spreadsheet_to_ensemble(input_file)
    
    # Print status of loaded ensemble
    print("\nBuilt the following ensemble\n")
    print(ens.species_df)
    print()

    return ens