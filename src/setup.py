from setuptools import setup, find_packages

print("""

- develop install: python setup.py develop
- build wheel: python setup.py bdist_wheel

""")

if __name__ == '__main__':
    packageName = 'task_man'

    setup(
        name=packageName,
        package_dir={"": "."},
        packages=find_packages(exclude='build,__pycache__,{}.egg-info,design,dist,docs,req,ReadMe.md'.format(packageName).split(',')),
        version='0.1.0',
        description='A Simple Task Management System',
        author='Mike CHAN Hon Ming',
        author_email='siumingdev@gmail.com',
        include_package_data=True,
    )
