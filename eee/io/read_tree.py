"""
Load a tree into an ete3 tree data structure.
"""

from eee._private.check.standard import check_int

import ete3
from ete3 import Tree

def read_tree(tree,fmt=None):
    """
    Load a tree into an ete3 tree data structure.

    Parameters
    ----------
    tree : ete3.Tree or dendropy.Tree or str
        some sort of tree. can be an ete3.Tree (returns self), a dendropy Tree
        (converts to newick and drops root), a newick file or a newick string.
    fmt : int or None
        format for reading tree from newick. 0-9 or 100. (See Notes for what
        these mean). If format is None, try to parse without a format descriptor,
        then these formats in numerical order.

    Returns
    -------
    tree : ete3.Tree
        an ete3 tree object.

    Notes
    -----
    `fmt` number is read directly by ete3. See their documentation for how these
    are read (http://etetoolkit.org/docs/latest/tutorial/tutorial_trees.html#reading-and-writing-newick-trees).
    As of ETE3.1.1, these numbers mean:

    + 0: flexible with support values
    + 1: flexible with internal node names
    + 2: all branches + leaf names + internal supports
    + 3: all branches + all names
    + 4: leaf branches + leaf names
    + 5: internal and leaf branches + leaf names
    + 6: internal branches + leaf names
    + 7: leaf branches + all names
    + 8: all names
    + 9: leaf names
    + 100: topology only

    """

    # Already an ete3 tree.
    if issubclass(type(tree),ete3.TreeNode):
        return tree

    # If we get here, we need to convert. If fmt is not specified, try to parse
    # without a format string.
    if fmt is None:

        try:
            t = Tree(tree)
        except ete3.parser.newick.NewickError:

            # Try all possible formats now, in succession
            w = "\n\nNo tree format specified. Going to try different\n"
            w += "formats. Please check output carefully.\n\n"
            print(w)

            formats = list(range(10))
            formats.append(100)

            t = None
            for f in formats:
                try:
                    t = Tree(tree,format=f)
                    w = f"\n\nSuccessfully parsed tree with format style {f}.\n"
                    w += "Please see ete3 documentation for details:\n\n"
                    w += "http://etetoolkit.org/docs/latest/tutorial/tutorial_trees.html#reading-and-writing-newick-trees\n\n"
                    print(w)
                    break

                except ete3.parser.newick.NewickError:
                    continue

            if t is None:
                err = "\n\nCould not parse tree!\n\n"
                raise ValueError(err)

    else:

        fmt = check_int(fmt,
                variable_name="fmt",
                minimum_allowed=0,
                maximum_allowed=100)
        if fmt > 9 and fmt != 100:
            err = "\nfmt must be a value between 0 and 9, or 100.\n\n"
            raise ValueError(err)

        # Try a conversion with the specified format
        t = Tree(tree,format=fmt)

    return t




