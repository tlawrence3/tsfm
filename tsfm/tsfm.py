# -*- coding: utf-8 -*-
import argparse
import sys
import os
import tsfm.MolecularInformation as MolecularInformation

def main():
     #Setup parser
    parser = argparse.ArgumentParser(description = "tsfm")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--infernal", type=argparse.FileType("r"), help="Structure file is in infernal format")
    group.add_argument("-c", "--cove", type=argparse.FileType("r"), help="Structure file is in cove format")
    group.add_argument("-t", "--text", type=argparse.FileType("r"), help="Structure file is in text format")
    group.add_argument("-f", "--file", action="store_true", help="use to read in previous results from file")
    parser.add_argument("-p", "--proc", type = int, default = os.cpu_count(), help="Maximum number of concurrent processes. Default is number of cores reported by the OS")
    parser.add_argument("-v","--inverse", action="store_true", help="calculate anti-determinates")
    parser.add_argument("-a", "--alpha", type=float, default=0.05, help="Alpha value used for statistical tests. Default = 0.05")
    parser.add_argument("-e", "--entropy", type=str, default = "NSB", help= "Method of entropy estimation. Either NSB or Miller. Default = NSB")
    parser.add_argument('--max', '-x', help="Maximum sample size to calculate the exact entropy of.", type=int)
    parser.add_argument('--logo', help='Produce function logo ps files', action="store_true")
    parser.add_argument("-B", help="Number of permutations. Default value is 100", type=int, default=0)
    parser.add_argument("-o", "--stdout", action="store_true", help="Print results to STDOUT")
    parser.add_argument("-M", help = "Specify method to correct p-values for multiple-comparisons. Current methods available: bonferroni, holm, hommel, BH, BY, and hochberg-simes. Default is BH", default = "fdr_bh")
    parser.add_argument("-j", "--jsd", action="store_true", help="")
    parser.add_argument("file_prefix", help="File prefix", nargs='+')
    args = parser.parse_args()

    logo_dict = {}

    if (args.file):
        results = {}
        for prefix in args.file_prefix:
            prefix_name = prefix.split("/")[-1]
            results[prefix_name] = MolecularInformation.FunctionLogoResults(prefix, from_file = True)
    else:
        if (args.text):
            for prefix in args.file_prefix:
                prefix_name = prefix.split("/")[-1]
                logo_dict[prefix_name] = MolecularInformation.FunctionLogo(args.text, "text")
        if (args.cove):
            for prefix in args.file_prefix:
                prefix_name = prefix.split("/")[-1]
                logo_dict[prefix_name] = MolecularInformation.FunctionLogo(args.cove, "cove")

        for prefix in args.file_prefix:
            prefix_name = prefix.split("/")[-1]
            logo_dict[prefix_name].parse_sequences(prefix)

        if (args.max):
            for key in logo_dict:
                logo_dict[key].calculate_exact(args.max, args.proc)
            if (args.inverse):
                for key in logo_dict:
                    logo_dict[key].calculate_exact(args.max, args.proc, inverse=True)

        if (args.B):
            perm_dict = {}
            for key in logo_dict:
                print("Generating permuted alignment data for {}".format(key), file=sys.stderr)
                logo_dict[key].permute(args.B, args.proc)
            for key in logo_dict:
                print("Calculating permutation information for {}".format(key), file=sys.stderr)
                perm_dict[key] = logo_dict[key].permInfo(args.entropy, args.proc)
            if (args.inverse):
                perm_inverse_dict = {}
                for key in logo_dict:
                    print("Calculating inverse permutation information for {}".format(key), file = sys.stderr)
                    perm_inverse_dict[key] = logo_dict[key].permInfo(args.entropy, args.proc, inverse = True)

        results = {}
        for key in logo_dict:
            results[key] = MolecularInformation.FunctionLogoResults(key, logo_dict[key].basepairs, logo_dict[key].pos, logo_dict[key].sequences,
                                             logo_dict[key].pairs, logo_dict[key].singles)
        
        if (args.entropy == "NSB"):
            for key in logo_dict:
                print("Calculating information statistics for {} using NSB estimator".format(key), file = sys.stderr)
                info, height_dict = logo_dict[key].calculate_entropy_NSB()
                results[key].add_information(info = info, height = height_dict)
                if (args.inverse):
                    print("Calculating inverse information statistics for {} using NSB estimator".format(key), file = sys.stderr)
                    info_inverse, height_dict_inverse = logo_dict[key].calculate_entropy_inverse_NSB()
                    results[key].add_information(info = info_inverse, height = height_dict_inverse, inverse = True)
        else:
            for key in logo_dict:
                print("Calculating information statistics using Miller-Maddow estimator")
                info, height_dict = logo_dict[key].calculate_entropy_MM()
                results[key].add_information(info = info, height = height_dict)
                if (args.inverse):
                    print("Calculating inverse using Miller-Maddow estimator")
                    info_inverse, height_dict_inverse = logo_dict[key].calculate_entropy_inverse_MM()
                    results[key].add_information(info = info_inverse, height = height_dict_inverse, inverse = True)

        if (args.B):
            print("Calculating p-values")
            for key in results:
                results[key].add_stats(perm_dict[key], args.M)
                if (args.inverse):
                    results[key].add_stats(perm_inverse_dict[key], args.M, inverse = True)

        if (args.stdout):
            for key in results:
                results[key].text_output()


        if (args.logo):
            for key in results:
                results[key].logo_output()

    if (args.jsd):
        distance = MolecularInformation.DistanceCalculator("jsd")
        distance.get_distance(results)

if __name__ == "__main__":
    main()