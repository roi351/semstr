#!/usr/bin/env python3

import os
import sys
from glob import glob

import configargparse
from ucca import ioutil

from semstr.cfgutil import add_verbose_arg, add_boolean_option
from semstr.convert import CONVERTERS
from semstr.evaluate import EVALUATORS, Scores

desc = """Convert files to UCCA standard format, convert back to the original format and evaluate.
"""


def main():
    argparser = configargparse.ArgParser(description=desc)
    argparser.add_argument("filenames", nargs="+", help="file names to convert and evaluate")
    add_verbose_arg(argparser, help="detailed evaluation output")
    add_boolean_option(argparser, "wikification", "Spotlight to wikify any named node (for AMR)")
    argparser.add_argument("-o", "--out-dir", help="output directory (if unspecified, files are not written)")
    args = argparser.parse_args()

    scores = []
    for pattern in args.filenames:
        filenames = glob(pattern)
        if not filenames:
            raise IOError("Not found: " + pattern)
        for filename in filenames:
            print("\rConverting '%s'" % filename, end="")
            if args.out_dir or args.verbose:
                print(flush=True)
            basename, ext = os.path.splitext(os.path.basename(filename))
            passage_format = ext.lstrip(".")
            converters = CONVERTERS.get(passage_format, CONVERTERS["amr"])
            evaluator = EVALUATORS.get(passage_format, EVALUATORS["amr"]).evaluate
            with open(filename, encoding="utf-8") as f:
                for passage, ref, passage_id in converters[0](f, passage_id=basename, return_original=True):
                    if args.out_dir:
                        os.makedirs(args.out_dir, exist_ok=True)
                        outfile = "%s/%s.xml" % (args.out_dir, passage.ID)
                        print("Writing '%s'..." % outfile, file=sys.stderr, flush=True)
                        ioutil.passage2file(passage, outfile)
                    try:
                        guessed = converters[1](passage, wikification=args.wikification, use_original=False)
                    except Exception as e:
                        raise ValueError("Error converting %s back from %s" % (filename, passage_format)) from e
                    if args.out_dir:
                        outfile = "%s/%s%s" % (args.out_dir, passage.ID, ext)
                        print("Writing '%s'..." % outfile, file=sys.stderr, flush=True)
                        with open(outfile, "w", encoding="utf-8") as f_out:
                            print("\n".join(guessed), file=f_out)
                    try:
                        s = evaluator(guessed, ref, verbose=args.verbose > 1)
                    except Exception as e:
                        raise ValueError("Error evaluating conversion of %s" % filename) from e
                    scores.append(s)
                    if args.verbose:
                        print(passage_id)
                        s.print()
    print()
    if args.verbose and len(scores) > 1:
        print("Aggregated scores:")
    Scores(scores).print()

    sys.exit(0)


if __name__ == '__main__':
    main()
