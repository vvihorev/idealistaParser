from fabric import Connection, task

c = Connection('vvihorev@netherlands')

@task
def test_deploy(c):
    c.local('git push')
    with c.cd('scripts/idealistaParser'):
        c.run('git reset --hard')
        c.run('git pull')

test_deploy(c)
c.close()
