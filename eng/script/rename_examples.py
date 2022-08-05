import os
import re
import glob
import logging


spec_repo_path = os.path.abspath('c:/github/azure-rest-api-specs')
example_repo_path = os.path.abspath('c:/github/azure-rest-api-specs-examples')
rp_name = 'compute'


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %X')

    rename_for_language('java')
    rename_for_language('js')
    rename_for_language('go')


def rename_for_language(lang: str):
    lang_dir = f'examples-{lang}'
    lang_ext = f'.{lang}'
    for filename in glob.glob(
            os.path.join(example_repo_path, 'specification', rp_name) + f'/**/{lang_dir}/**/*.json',
            recursive=True):

        filename = os.path.abspath(filename)
        rel_filename = os.path.relpath(filename, example_repo_path)

        if lang_dir in rel_filename:
            spec_rel_filename = rel_filename.replace(lang_dir, 'examples')

            spec_filename = os.path.abspath(os.path.join(spec_repo_path, spec_rel_filename))
            if not os.path.isfile(spec_filename):
                logging.warning(f'Not found {spec_rel_filename}')

                name = os.path.basename(spec_rel_filename)
                api_version = re.match(r'.*(\d\d\d\d-\d\d-\d\d).*', spec_rel_filename).group(1)

                spec_filenames = glob.glob(
                    os.path.join(spec_repo_path, 'specification', rp_name) + f'/**/{api_version}/**/{name}',
                    recursive=True)

                spec_filename_found = os.path.abspath(spec_filenames[0])
                logging.info(f'Found possible example {spec_filename_found}')

                filename_found = os.path.abspath(os.path.join(
                    example_repo_path,
                    os.path.relpath(spec_filename_found, spec_repo_path).replace('examples', lang_dir)))

                logging.info(f'Rename {filename} to {filename_found}')
                os.makedirs(os.path.dirname(filename_found), exist_ok=True)
                try:
                    os.rename(filename, filename_found)
                    os.rename(filename.replace('.json', lang_ext), filename_found.replace('.json', lang_ext))
                except FileExistsError as error:
                    logging.error(f'File already exists {filename_found}')


if __name__ == '__main__':
    main()
