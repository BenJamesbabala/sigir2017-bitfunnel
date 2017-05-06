import os
import re
from bf_utilities import run

def execute(command, log_file = None):
    print(command)
    run(command, os.getcwd(), log_file)
    print("Finished")
    print()


class Experiment:
    def __init__(self,
                 bf_executables,
                 lucene_repo,
                 mg4j_repo,
                 pef_executables,
                 index_root,
                 basename,
                 chunk_dir,
                 chunk_pattern,
                 queries):

        self.bf_executable = bf_executables
        self.mg4j_repo = mg4j_repo
        self.pef_executable = pef_executables
        self.lucene_repo = lucene_repo

        self.index_root = index_root

        self.chunk_dir = chunk_dir
        self.chunk_pattern = chunk_pattern
        self.basename = basename
        self.queries = queries;

        self.thread_count = 8
        self.pef_index_type = 'opt'

        self.update()


    # update() recalculates properties derived from constructor parameters.
    # For convenience, one can change any of the members directly initialized
    # in the constructor and then call update() to regenerate the derived
    # members.
    def update(self):
        # TODO: Consider copying manifest into root.
        # TODO: What if manifest already exists? Consider pre-verification step that catches errors up front.
        # TODO: Consider basing root name off of manifest name.
        self.root = os.path.join(self.index_root, self.basename)

        self.bf_index_path = os.path.join(self.root, "bitfunnel")
        self.lucene_index_path = os.path.join(self.root, "lucene")
        self.mg4j_index_path = os.path.join(self.root, "mg4j")
        self.pef_index_path = os.path.join(self.root, "pef")

        self.manifest = os.path.join(self.root, self.basename + "-manifest.txt")

        # BitFunnel variables
        # TODO: don't hard code density.
        self.bf_density = 0.15
        self.bf_repl_script = os.path.join(self.bf_index_path, self.basename + "-repl.script")
        self.bf_shard_definition = os.path.join(self.bf_index_path, "ShardDefinition.csv")
        self.bf_build_statistics_log = os.path.join(self.bf_index_path, "build_bf_statistics_log.txt")
        self.bf_build_term_table_log = os.path.join(self.bf_index_path, "build_bf_term_table_log.txt")
        self.bf_run_queries_log = os.path.join(self.bf_index_path, "run_bf_queries_log.txt")

        # Lucene variables.
        self.lucene_classpath = os.path.join(self.lucene_repo, "target", "lucene-runner-1.0-SNAPSHOT.jar")
        self.lucene_run_queries_log = os.path.join(self.lucene_index_path, "run_lucene_queries_log.txt")

        # mg4j variables
        self.mg4j_classpath = os.path.join(self.mg4j_repo, "target", "mg4j-1.0-SNAPSHOT-jar-with-dependencies.jar")
        self.mg4j_basename = os.path.join(self.mg4j_index_path, self.basename)
        self.mg4j_build_index_log = os.path.join(self.mg4j_index_path, "build_mg4j_index_log.txt")
        self.mg4j_filter_queries_log = os.path.join(self.mg4j_index_path, "filter_mg4j_queries_log.txt")
        self.mg4j_run_queries_log = os.path.join(self.mg4j_index_path, "run_mg4j_queries_log.txt")

        # Partitioned ELias-Fano variables
        self.pef_basename = os.path.join(self.pef_index_path, self.basename)
        self.pef_collection = os.path.join(self.pef_index_path, self.basename)
        # TODO: don't hard-code opt
        self.pef_index_file = os.path.join(self.pef_index_path, self.basename + ".index." + self.pef_index_type)
        self.pef_creator = os.path.join(self.pef_executable, "create_freq_index")
        self.pef_runner = os.path.join(self.pef_executable, "Runner")
        self.pef_build_collection_log = os.path.join(self.pef_index_path, "build_pef_collection_log.txt")
        self.pef_build_index_log = os.path.join(self.pef_index_path, "build_pef_index_log.txt")
        self.pef_run_queries_log = os.path.join(self.pef_index_path, "run_pef_queries_log.txt")


        # Query-related variables
        self.queries_basename = os.path.basename(self.queries)
        self.query_path = os.path.join(self.root, "queries")
        self.root_query_file = os.path.join(self.query_path, self.queries_basename)

        # TODO: mapping to filtered query file is in Java right now. Can this be moved here?
        self.pef_query_file = os.path.join(self.query_path, self.queries_basename + "-in-index-ints.txt")
        self.filtered_query_file = os.path.join(self.query_path, self.queries_basename + "-in-index.txt")

        self.pef_results_file = os.path.join(self.pef_index_path, self.queries_basename + "-results.csv")
        self.mg4j_results_file = os.path.join(self.mg4j_index_path, self.queries_basename + "-results.csv")



    ###########################################################################
    #
    # Query log cleaning
    #
    ###########################################################################

    def fix_query_log(self):
        if not os.path.exists(self.query_path):
            os.makedirs(self.query_path)
        print("fixing {0} ==> {1}".format(self.queries, self.root_query_file))
        # We use this encoding because the default is UTF-8 and trec efficiency is not UTF-8.
        # We don't know if this is the correct encoding and may read bogus queries.
        with open(self.queries, 'r', encoding="ISO-8859-1") as f, open(self.root_query_file, 'w') as out:
            for line in f:
                # Remove leading line numbers.
                step1 = re.sub(r"\A\d+:", '', line)

                # Remove punctuation and then coalesce spaces and remove
                # leading and trailing spaces.
                step2 = ' '.join(re.sub(r"[-;:,&'\+\./\(\)]", ' ', step1).split())

                # Write to output file.
                if len(step2) > 0:
                    print(step2, file=out)


    ###########################################################################
    #
    # mg4j
    #
    ###########################################################################

    def build_mg4j_index(self):
        args = ("java -cp {0} "
                "it.unimi.di.big.mg4j.tool.IndexBuilder "
                "-o org.bitfunnel.reproducibility.ChunkManifestDocumentSequence\({1}\) "
                "{2}").format(self.mg4j_classpath, self.manifest, self.mg4j_basename)
        if not os.path.exists(self.mg4j_index_path):
            os.makedirs(self.mg4j_index_path)
        execute(args, self.mg4j_build_index_log)


    def run_mg4j_queries(self):
        args = ("java -cp {0} "
                "org.bitfunnel.reproducibility.QueryLogRunner "
                "-t {1} {2} {3} {4}").format(self.mg4j_classpath,
                                             self.thread_count,
                                             self.mg4j_basename,
                                             self.filtered_query_file,
                                             self.mg4j_results_file)
        execute(args, self.mg4j_run_queries_log)


    def filter_query_log(self):
        args = ("java -cp {0} "
                "org.bitfunnel.reproducibility.IndexExporter "
                "{1} {2} "
                "--queries {3}").format(self.mg4j_classpath,
                                        self.mg4j_basename,
                                        self.query_path,
                                        self.root_query_file);
        execute(args, self.mg4j_filter_queries_log)


    ###########################################################################
    #
    # Partitioned Elias-Fano (PEF)
    #
    ###########################################################################

    def build_pef_collection(self):
        if not os.path.exists(self.pef_index_path):
            os.makedirs(self.pef_index_path)

        args = ("java -cp {0} "
                "org.bitfunnel.reproducibility.IndexExporter "
                "{1} {2} --index").format(self.mg4j_classpath, self.mg4j_basename, self.pef_basename);
        execute(args, self.pef_build_collection_log)


    def build_pef_index(self):
        args = ("{0} {1} {2} {3}").format(self.pef_creator,
                                          self.pef_index_type,
                                          self.pef_collection,
                                          self.pef_index_file)
        execute(args, self.pef_build_index_log)


    def pef_index_from_mg4j_index(params):
        params.build_pef_collection()
        params.build_pef_index()


    def run_pef_queries(self):
        args = ("{0} {1} {2} {3} {4} {5}").format(self.pef_runner,
                                               self.pef_index_type,
                                               self.pef_index_file,
                                               self.pef_query_file,
                                               self.thread_count,
                                               self.pef_results_file)
        execute(args, self.pef_run_queries_log)


    ###########################################################################
    #
    # BitFunnel
    #
    ###########################################################################
    def build_bf_index(self):
        if not os.path.exists(self.bf_index_path):
            os.makedirs(self.bf_index_path)

        # We're currently restricted to a single shard,
        # so create an empty ShardDefinition file.
        # TODO: reinstate following line.
        open(self.bf_shard_definition, "w").close()

        # Run statistics builder
        args = ("{0} statistics {1} {2}").format(self.bf_executable,
                                             self.manifest,
                                             self.bf_index_path)
        execute(args, self.bf_build_statistics_log)

        # Run termtable builder
        # TODO: don't hard code Optimal.
        # TODO: don't hard code SNR.
        args = ("{0} termtable {1} {2} Optimal").format(self.bf_executable,
                                                        self.bf_index_path,
                                                        self.bf_density)
        execute(args, self.bf_build_term_table_log)


    def run_bf_queries(self):
        # Create script file
        # TODO: reinstate following lines.
        with open(self.bf_repl_script, "w") as file:
        # file = sys.stdout
            for i in range(0,1):
                file.write("load manifest {0}\n".format(self.manifest));
                file.write("status\n");
                file.write("compiler\n");
                for t in range(1, self.thread_count + 1):
                    results_dir = os.path.join(self.bf_index_path, "results-{0}".format(t))
                    if not os.path.exists(results_dir):
                        print("mkdir " + results_dir)
                        os.makedirs(results_dir)
                    file.write("threads {0}\n".format(t))
                    file.write("cd {0}\n".format(results_dir))
                    file.write("query log {0}\n".format(self.filtered_query_file))

                file.write("quit\n")

        # Start BitFunnel repl
        args = ("{0} repl {1} -script {2}").format(self.bf_executable,
                                                   self.bf_index_path,
                                                   self.bf_repl_script)
        execute(args, self.bf_run_queries_log)




    ###########################################################################
    #
    # Lucene
    #
    ###########################################################################
    def build_lucene_index(self):
        # if not os.path.exists(self.lucene_index_path):
        #     print("mkdir " + self.lucene_index_path)
        #     os.makedirs(self.lucene_index_path)
        args = ("java -cp {0} "
                "org.bitfunnel.runner.IndexBuilder "
                "{1} {2} {3}").format(self.lucene_classpath,
                                      self.lucene_index_path,
                                      self.manifest,
                                      self.thread_count)
        print(args)
        execute(args, self.lucene_run_queries_log)


    def run_lucene_queries(self):
        args = ("java -cp {0} "
                "org.bitfunnel.runner.LuceneRunner "
                "{1} {2} {3}").format(self.lucene_classpath,
                                      self.lucene_index_path,
                                      self.filtered_query_file,
                                      self.thread_count)
        print(args)
        execute(args, self.lucene_run_queries_log)


    ###########################################################################
    #
    # Chunk manifests
    #
    ###########################################################################
    def build_chunk_manifest(self):
        if not os.path.exists(self.root):
            os.makedirs(self.root)

        regex = re.compile(self.chunk_pattern)
        chunks = [os.path.join(self.chunk_dir, f)
                  for root, dirs, files in os.walk(self.chunk_dir)
                  for f in files
                  if regex.search(f) is not None]

        for chunk in chunks:
            print(chunk)

        print("Writing manifest {0}".format(self.manifest))
        with open(self.manifest, 'w') as file:
            for chunk in chunks:
                file.write(chunk + '\n')



experiment_windows_273_150_100 = Experiment(
    # Paths to tools
    r"D:\git\BitFunnel\build-msvc\tools\BitFunnel\src\Release\BitFunnel.exe",
    r"D:\git\LuceneRunner",
    r"D:\git\mg4j-workbench",
    r"/home/mhop/git/partitioned_elias_fano/bin",

    # The directory containing all indexes and the basename for this index
    r"D:\temp\indexes",
    r"273-150-100",

    # The directory with the gov2 chunks and the regular expression pattern
    # used to determine which chunks will be used for this experiment.
    r"d:\sigir\chunks-100-150",
    r"GX.*",  # Use all chunks

    # The query log to be used for this experiment.
    r"D:\sigir\queries\06.efficiency_topics.all"
)

experiment_windows_273_1000_1500 = Experiment(
    # Paths to tools
    r"D:\git\BitFunnel\build-msvc\tools\BitFunnel\src\Release\BitFunnel.exe",
    r"D:\git\LuceneRunner",
    r"D:\git\mg4j-workbench",
    r"/home/mhop/git/partitioned_elias_fano/bin",

    # The directory containing all indexes and the basename for this index
    r"D:\temp\indexes",
    r"273-1000-1500",

    # The directory with the gov2 chunks and the regular expression pattern
    # used to determine which chunks will be used for this experiment.
    r"d:\sigir\chunks-1000-1500",
    r"GX.*",  # Use all chunks

    # The query log to be used for this experiment.
    r"D:\sigir\queries\06.efficiency_topics.all"
)

experiment_linux = Experiment(
    # Paths to tools
    r"/home/mhop/git/BitFunnel/build-make/tools/BitFunnel/src/BitFunnel",
    r"/home/mhop/git/LuceneRunner",
    r"/home/mhop/git/mg4j-workbench",
    r"/home/mhop/git/partitioned_elias_fano/bin",

    # The directory containing all indexes and the basename for this index
    r"/mnt/d/temp/indexes",
    r"273-150-100",

    # The directory with the gov2 chunks and the regular expression pattern
    # used to determine which chunks will be used for this experiment.
    r"/mnt/d/sigir/chunks-100-150",
    r"GX.*",  # Use all chunks

    # The query log to be used for this experiment.
    r"/home/mhop/git/mg4j-workbench/data/trec-terabyte/06.efficiency_topics.all"
)

experiment_dl_linux = Experiment(
    # Paths to tools
    r"/home/danluu/dev/BitFunnel/build-ninja/tools/BitFunnel/src/BitFunnel",
    r"/home/danluu/dev/LuceneRunner",
    r"/home/danluu/dev/mg4j-workbench",
    r"/home/danluu/dev/partitioned_elias_fano/bin",

    # The directory containing all indexes and the basename for this index
    r"/home/danluu/dev/what-is-this",
    r"273-128-255",

    # The directory with the gov2 chunks and the regular expression pattern
    # used to determine which chunks will be used for this experiment.
    r"/home/danluu/dev/gov2",
    r"GX000.*",  # Use all chunks

    # The query log to be used for this experiment.
    r"/home/danluu/Downloads/06.efficiency_topics.all"
)

def runxxx(experiment):
    # experiment.fix_query_log()
    # experiment.build_chunk_manifest()
    # experiment.build_mg4j_index()
    # experiment.filter_query_log()
    # experiment.run_lucene_queries()
    # experiment.run_mg4j_queries()
    # experiment.build_bf_index()
    # experiment.run_bf_queries()
    # experiment.build_lucene_index()
    experiment.run_lucene_queries()
    # experiment.pef_index_from_mg4j_index()
    # experiment.run_pef_queries()

runxxx(experiment_windows_273_150_100)


