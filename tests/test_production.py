import contextlib
import copy
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from radio.production import (ProductionError, initialize, validate_domain,
                              validate_config, preflight, start, main)
from radio.config import Config
from radio.watchdog import Options


def model():
    source='Qm5_T8xZs4-2N6yK9vR3aC7dF1gH0jLpUwE'
    admin='Rs7_D2xYu9-5M1qJ8wT6bE3fG0hK4nVzAcP'
    common={'RADIO_DATA':'/data','STATION_SEED':'42','SEGMENT_SECONDS':'120',
            'BUFFER_SECONDS':'1200','BPM':'60','MUSICAL_MEMORY':'1',
            'ICECAST_SOURCE_PASSWORD':source,'ICECAST_ADMIN_PASSWORD':admin}
    services={}
    for role in ['composer','renderer','broadcaster','icecast','web']:
        services[role]={'user':'10001:10001','read_only':True,'cap_drop':['ALL'],
                        'security_opt':['no-new-privileges:true'],'networks':{'default':None},
                        'tmpfs':['/tmp:rw,noexec,nosuid,size=64m,mode=1777'],
                        'environment':dict(common),'volumes':[{'type':'volume','source':'radio-data','target':'/data'}]}
    services['icecast']['ports']=[{'host_ip':'127.0.0.1','published':'8000','target':8000,'protocol':'tcp'}]
    services['web']['tmpfs'].append('/config:ro,noexec,nosuid,size=1m,uid=10001,gid=10001,mode=0700')
    services['web']['environment']={'RADIO_DOMAIN':'radio.my-station.net'}
    services['web']['volumes']=[{'type':'volume','source':'web-tls','target':'/data'}]
    services['web']['ports']=[{'published':'80','target':8080,'protocol':'tcp'}, {'published':'443','target':8443,'protocol':'tcp'}]
    return {'services':services,'networks':{'default':{'name':'radio-test_default','ipam':{}}},'volumes':{'radio-data':{},'web-tls':{}}}


class ProductionTests(unittest.TestCase):
    def test_hostname_canonicalization_and_injection_rejection(self):
        self.assertEqual(validate_domain('Radio.My-Station.NET'),'radio.my-station.net')
        for domain in ['localhost','radio.localhost','127.0.0.1','::1','https://radio.my-station.net','radio.my-station.net:443','radio.my-station.net/path','*.my-station.net','radio.example.com','radio.invalid','a..net','-radio.net','radio.net\nOTHER=value','radio.net ']:
            with self.subTest(domain=domain),self.assertRaises(ProductionError):validate_domain(domain)

    def test_generated_config_is_complete_private_random_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env.production'
            initialize(path,'radio.my-station.net',station_seed=42)
            original=path.read_text();values=dict(line.split('=',1) for line in original.splitlines() if line and not line.startswith('#'))
            source=values['ICECAST_SOURCE_PASSWORD'];admin=values['ICECAST_ADMIN_PASSWORD']
            self.assertNotEqual(source,admin);self.assertGreaterEqual(len(source),32)
            self.assertEqual(values['STATION_SEED'],'42')
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            with self.assertRaises((ProductionError,FileExistsError)):initialize(path,'other.my-station.net')
            self.assertEqual(path.read_text(),original)
            self.assertEqual(list(Path(temp).iterdir()),[path])

    def test_generator_never_follows_existing_or_broken_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);target=root/'untouched';target.write_text('keep')
            link=root/'.env.production';link.symlink_to(target)
            with self.assertRaises((ProductionError,FileExistsError)):initialize(link,'radio.my-station.net')
            self.assertEqual(target.read_text(),'keep')
            link.unlink();link.symlink_to(root/'absent')
            with self.assertRaises((ProductionError,FileExistsError)):initialize(link,'radio.my-station.net')
            self.assertFalse((root/'absent').exists())

    def test_generator_diagnostics_and_failed_write_do_not_publish_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env.production';out=io.StringIO()
            with patch('sys.argv',['production','init','--domain','radio.my-station.net','--env-file',str(path)]),contextlib.redirect_stdout(out):main()
            for key,value in (line.split('=',1) for line in path.read_text().splitlines() if '=' in line):
                if 'PASSWORD' in key:self.assertNotIn(value,out.getvalue())
            other=Path(temp)/'.env.other'
            with patch('radio.production.os.link',side_effect=OSError('disk full')):
                with self.assertRaises((ProductionError,OSError)):initialize(other,'radio.my-station.net')
            self.assertFalse(other.exists())
            self.assertEqual(list(Path(temp).iterdir()),[path])

    def test_pure_runtime_parsers_do_not_create_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/'absent'
            self.assertEqual(Config.from_env({'RADIO_DATA':str(data)}).data,data)
            self.assertFalse(data.exists())
            self.assertEqual(Options.load(env={'WATCHDOG_PROBE_SECONDS':'1','WATCHDOG_TIMEOUT_SECONDS':'8'}).probe_seconds,1)

    def test_resolved_valid_config_returns_only_public_summary(self):
        cfg=model();summary=validate_config(cfg)
        self.assertEqual(summary['domain'],'radio.my-station.net')
        text=json.dumps(summary)
        self.assertNotIn(cfg['services']['icecast']['environment']['ICECAST_SOURCE_PASSWORD'],text)
        self.assertNotIn('PASSWORD',text)

    def test_missing_weak_shared_or_inconsistent_credentials_are_rejected(self):
        for value in ['', 'local-source-change-me','replace-with-a-long-random-password-123456789','a'*43]:
            cfg=model()
            for role in ['composer','renderer','broadcaster','icecast']:cfg['services'][role]['environment']['ICECAST_SOURCE_PASSWORD']=value
            with self.subTest(value=value),self.assertRaises(ProductionError):validate_config(cfg)
        cfg=model();env=cfg['services']['icecast']['environment'];env['ICECAST_ADMIN_PASSWORD']=env['ICECAST_SOURCE_PASSWORD']
        with self.assertRaises(ProductionError):validate_config(cfg)
        cfg=model();cfg['services']['broadcaster']['environment']['ICECAST_SOURCE_PASSWORD']='Different_VeryLong_Source_Credential_123456789'
        with self.assertRaises(ProductionError):validate_config(cfg)

    def test_public_admin_extra_ports_unsafe_mounts_and_privileges_are_rejected(self):
        def public_admin(c):c['services']['icecast']['ports'][0]['host_ip']='0.0.0.0'
        def extra_port(c):c['services']['web']['ports'].append({'published':'8080','target':8080})
        def unsafe_mount(c):c['services']['web']['volumes'].append({'type':'volume','source':'radio-data','target':'/station'})
        def root(c):c['services']['web']['user']='0:0'
        def writable(c):c['services']['renderer']['read_only']=False
        def privileged(c):c['services']['composer']['privileged']=True
        def host_net(c):c['services']['web']['network_mode']='host'
        def caps(c):c['services']['web']['cap_drop']=[]
        def nnp(c):c['services']['icecast']['security_opt']=[]
        for mutation in [public_admin,extra_port,unsafe_mount,root,writable,privileged,host_net,caps,nnp]:
            cfg=model();mutation(cfg)
            with self.subTest(mutation=mutation.__name__),self.assertRaises(ProductionError):validate_config(cfg)

    def test_invalid_music_or_watchdog_values_do_not_leak_input_in_diagnostics(self):
        marker='SecretValueThatMustNotBePrinted'
        for role,key in [('renderer','BPM'),('broadcaster','WATCHDOG_TIMEOUT_SECONDS')]:
            cfg=model();cfg['services'][role]['environment'][key]=marker
            with self.assertRaises(ProductionError) as error:validate_config(cfg)
            self.assertNotIn(marker,str(error.exception))

    def test_preflight_requires_private_file_and_sanitizes_docker_failures(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env.production';path.write_text('test');path.chmod(0o644)
            with patch('radio.production.subprocess.run') as run:
                with self.assertRaises(ProductionError):preflight(path)
                run.assert_not_called()
            path.chmod(0o600)
            marker='DoNotLeakSecretFromComposeOutput'
            with patch('radio.production.subprocess.run',side_effect=subprocess.CalledProcessError(1,['docker'],output=marker,stderr=marker)):
                with self.assertRaises(ProductionError) as error:preflight(path)
                self.assertNotIn(marker,str(error.exception))

    def test_failed_preflight_never_starts_containers(self):
        with patch('radio.production.preflight',side_effect=ProductionError('invalid')),patch('radio.production.subprocess.run') as run:
            with self.assertRaises(ProductionError):start(Path('.env.production'))
            run.assert_not_called()

    def test_duplicate_or_unbounded_temporary_mounts_are_rejected(self):
        cfg=model();cfg['services']['composer']['tmpfs'].append(cfg['services']['composer']['tmpfs'][0])
        with self.assertRaises(ProductionError):validate_config(cfg)
        cfg=model();cfg['services']['composer']['tmpfs'][0]+=",size=2048m"
        with self.assertRaises(ProductionError):validate_config(cfg)

    def test_configs_secrets_and_inherited_mounts_cannot_bypass_volume_policy(self):
        for key in ['configs', 'secrets', 'volumes_from']:
            cfg=model();cfg['services']['web'][key]=[{'source':'host_file','target':'/srv/host-file.txt'}]
            with self.subTest(key=key),self.assertRaises(ProductionError):validate_config(cfg)
        for key in ['configs','secrets']:
            cfg=model();cfg[key]={'host_file':{'file':'/etc/passwd'}}
            with self.subTest(key=key),self.assertRaises(ProductionError):validate_config(cfg)

    def test_only_the_ordinary_project_bridge_is_permitted(self):
        for network in [{'driver':'macvlan','driver_opts':{'parent':'eth0'}},
                        {'external':True,'name':'host'}, {'driver':'host'}]:
            cfg=model();cfg['networks']['default']=network
            with self.subTest(network=network),self.assertRaises(ProductionError):validate_config(cfg)
        for key,value in [('network_mode','service:icecast'), ('networks',{'other':None}),
                          ('networks',{'default':{'ipv4_address':'192.0.2.5'}})]:
            cfg=model();cfg['services']['web'][key]=value
            with self.subTest(key=key),self.assertRaises(ProductionError):validate_config(cfg)

    def test_conflicting_temporary_permissions_are_rejected(self):
        for options in [',exec', ',suid', ',ro', ',size=64m']:
            cfg=model();cfg['services']['composer']['tmpfs'][0]+=options
            with self.subTest(options=options),self.assertRaises(ProductionError):validate_config(cfg)
        cfg=model();cfg['services']['web']['tmpfs'][1]+=',rw'
        with self.assertRaises(ProductionError):validate_config(cfg)

    def test_read_only_custom_soundfont_is_supported_without_sharing_it_with_web(self):
        with tempfile.TemporaryDirectory() as temp:
            font=Path(temp)/'custom.sf2';font.write_bytes(b'owned font fixture')
            cfg=model();renderer=cfg['services']['renderer'];renderer['environment']['SOUNDFONT']='/soundfonts/custom.sf2'
            renderer['volumes'].append({'type':'bind','source':str(font),'target':'/soundfonts/custom.sf2','read_only':True})
            self.assertEqual(validate_config(cfg)['domain'],'radio.my-station.net')
            renderer['volumes'][1]['read_only']=False
            with self.assertRaises(ProductionError):validate_config(cfg)

    def test_start_checks_public_tls_after_health_and_does_not_rollback_on_failure(self):
        from radio.production import probe_https
        command=['docker','compose','--project-name','owned-radio']
        summary={'domain':'radio.my-station.net'}
        with patch('radio.production.preflight',return_value=(command,summary)),patch('radio.production._run',return_value='') as run,patch('radio.production.probe_https',return_value={'page_verified':True,'stream_verified':True}) as probe:
            result=start(Path('.env.production'))
            self.assertTrue(result['stream_verified']);self.assertIn('up',run.call_args[0][0])
            probe.assert_called_once_with('https://radio.my-station.net')
        with patch('radio.production.preflight',return_value=(command,summary)),patch('radio.production._run',return_value='') as run,patch('radio.production.probe_https',side_effect=ProductionError('not ready')),patch('radio.production.time.monotonic',side_effect=[0,100]):
            with self.assertRaisesRegex(ProductionError,'left running'):start(Path('.env.production'))
            self.assertEqual(run.call_count,1)
        with self.assertRaises(ProductionError):probe_https('http://radio.my-station.net')


if __name__=='__main__':unittest.main()
