import io
import json
import sqlite3
import tempfile
import threading
import time
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from .services import link_download as service
from .db.task_history import ensure_schema as task_schema, list_tasks

HOST = 'http://pickupphoto.nextsls.com:30233/photo/image?id=example-id&extra=keep'

class LinkDownloadTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.db = SimpleNamespace(conn=self.conn,lock=threading.RLock())
        task_schema(self.conn); service.ensure_schema(self.conn)
    def tearDown(self): self.conn.close()
    def test_rule_preserves_query_and_rejects_untrusted(self):
        view,download,_ = service.resolve_link(HOST.replace('http:', 'http\\:'))
        self.assertEqual(view,HOST)
        self.assertEqual(download,HOST.replace('/image?', '/image/pack?'))
        for url in ['http://localhost/photo/image?id=x',HOST.replace('nextsls.com','nextsls.com.evil.invalid'),HOST.replace('30233','80'),HOST.replace('example-id',''),HOST+'#fragment',HOST.replace('http://','http://user:secret@')]:
            with self.assertRaises(ValueError): service.resolve_link(url)
    def test_duplicate_and_path_names_rejected(self):
        for rows in [[{'shipmentNo':'../bad','url':HOST}],[{'shipmentNo':'CON','url':HOST}],[{'shipmentNo':'EXAMPLE','url':HOST},{'shipmentNo':'example','url':HOST}]]:
            with self.assertRaises(ValueError): service.validate_rows(rows)
    def test_partial_success_bundle_and_expiry(self):
        rows = service.validate_rows([{'shipmentNo':'EXAMPLE-A','url':HOST},{'shipmentNo':'EXAMPLE-B','url':HOST}])
        job = {'id':'example-job','created':time.time(),'status':'running','rows':rows}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def fake_fetch(item,folder,*args):
                if item['shipmentNo']=='EXAMPLE-B': return {'status':'failed','message':'timeout'}
                filename='EXAMPLE-A.zip'
                with zipfile.ZipFile(folder/filename,'w') as archive: archive.writestr('example.txt','example')
                return {'status':'success','message':'ok','filename':filename}
            service._active.add(job['id'])
            with patch.object(service,'_fetch',side_effect=fake_fetch): service._run(self.db,root,job)
            restored=service.get_job(self.db,job['id'])
            self.assertEqual(restored['status'],'done')
            path,_=service.download_path(self.db,root,job['id'])
            with zipfile.ZipFile(path) as archive: self.assertEqual(archive.namelist(),['EXAMPLE-A.zip'])
            self.assertEqual(list_tasks(self.db)[0]['managedBy'],'server')
            with self.assertRaises(ValueError): service.download_path(self.db,root,job['id'],1)
            job['created']=time.time()-service.RETENTION_SEC-1; service._save(self.db,job)
            with self.assertRaises(ValueError): service.download_path(self.db,root,job['id'])
    def test_restart_marks_unfinished_rows(self):
        job={'id':'interrupted','created':time.time(),'status':'running','rows':service.validate_rows([{'shipmentNo':'EXAMPLE','url':HOST}])}
        service._save(self.db,job)
        restored=service.get_job(self.db,job['id'])
        self.assertTrue(restored['interrupted'])
        self.assertEqual(restored['rows'][0]['status'],'failed')

    def test_cleanup_failure_keeps_original_error_and_packages_other_rows(self):
        rows = service.validate_rows([
            {'shipmentNo': 'EXAMPLE-A', 'url': HOST},
            {'shipmentNo': 'EXAMPLE-B', 'url': HOST.replace('example-id', 'invalid-zip')},
        ])
        job = {'id': 'cleanup-failure', 'created': time.time(), 'status': 'running', 'rows': rows}
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('example.txt', 'example')

        def get_response(url, **kwargs):
            content = b'incomplete file' if 'invalid-zip' in url else data.getvalue()
            return nullcontext(SimpleNamespace(status_code=200, headers={}, iter_content=lambda _: [content]))

        original_unlink = Path.unlink

        def deny_partial_cleanup(path, *args, **kwargs):
            if path.name == 'EXAMPLE-B.zip.part':
                raise PermissionError('simulated file lock')
            return original_unlink(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch.object(service.requests, 'Session', return_value=nullcontext(SimpleNamespace(get=get_response))),
                patch.object(Path, 'unlink', deny_partial_cleanup),
                self.assertLogs(service.logger, level='WARNING') as logs,
            ):
                service._run(self.db, root, job)

            restored = service.get_job(self.db, job['id'])
            self.assertEqual(restored['status'], 'done')
            self.assertEqual(restored['rows'][0]['status'], 'success')
            self.assertEqual(restored['rows'][1]['status'], 'failed')
            self.assertIn('不是有效 ZIP', restored['rows'][1]['message'])
            self.assertTrue((root / job['id'] / 'EXAMPLE-B.zip.part').is_file())
            self.assertIn('EXAMPLE-B.zip.part', logs.output[0])
            bundle, _ = service.download_path(self.db, root, job['id'])
            with zipfile.ZipFile(bundle) as archive:
                self.assertEqual(archive.namelist(), ['EXAMPLE-A.zip'])
    def test_html_is_not_downloaded_as_zip(self):
        response=SimpleNamespace(status_code=200,headers={'Content-Type':'text/html'})
        class Context:
            def __init__(self,value): self.value=value
            def __enter__(self): return self.value
            def __exit__(self,*args): pass
        session=SimpleNamespace(get=lambda *a,**kw:Context(response))
        with tempfile.TemporaryDirectory() as tmp,patch.object(service.requests,'Session',return_value=Context(session)):
            result=service._fetch({'shipmentNo':'EXAMPLE','downloadUrl':HOST},Path(tmp),[0],threading.Lock())
            self.assertEqual(result['status'],'failed')
            self.assertIn('网页',result['message'])

    def test_cleanup_is_scoped_to_registered_expired_uuid(self):
        import uuid
        job_id=str(uuid.uuid4())
        job={'id':job_id,'created':time.time()-service.RETENTION_SEC-1,'status':'done','rows':service.validate_rows([{'shipmentNo':'EXAMPLE','url':HOST}])}
        service._save(self.db,job)
        root=Path('synthetic-download-root')
        with patch.object(Path,'is_dir',return_value=True), patch.object(service.shutil,'rmtree') as remove:
            service.purge_expired_files(self.db,root)
            remove.assert_called_once_with(root/job_id)
        self.assertEqual(len(list_tasks(self.db)),1)

    def test_failed_transfer_cleans_partial_and_keeps_existing_completed_zip(self):
        class Context:
            def __init__(self,value): self.value=value
            def __enter__(self): return self.value
            def __exit__(self,*args): pass
        class Response:
            status_code=200
            headers={'Content-Type':'application/zip'}
            def iter_content(self,*args):
                yield b'partial-download'
                raise service.requests.ReadTimeout('example timeout')
        session=SimpleNamespace(get=lambda *a,**kw:Context(Response()))
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            target=folder/'EXAMPLE.zip'
            with zipfile.ZipFile(target,'w') as archive: archive.writestr('example.txt','original')
            original=target.read_bytes()
            with patch.object(service.requests,'Session',return_value=Context(session)):
                result=service._fetch({'shipmentNo':'EXAMPLE','downloadUrl':HOST},folder,[0],threading.Lock())
            self.assertEqual(result['status'],'failed')
            self.assertFalse((folder/'EXAMPLE.zip.part').exists())
            self.assertEqual(target.read_bytes(),original)

    def test_success_promotes_validated_partial_file(self):
        class Context:
            def __init__(self,value): self.value=value
            def __enter__(self): return self.value
            def __exit__(self,*args): pass
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as archive: archive.writestr('example.txt','example')
        response=SimpleNamespace(status_code=200,headers={'Content-Type':'application/zip'},iter_content=lambda *args:[data.getvalue()])
        session=SimpleNamespace(get=lambda *a,**kw:Context(response))
        with tempfile.TemporaryDirectory() as tmp,patch.object(service.requests,'Session',return_value=Context(session)):
            folder=Path(tmp)
            result=service._fetch({'shipmentNo':'EXAMPLE','downloadUrl':HOST},folder,[0],threading.Lock())
            self.assertEqual(result['status'],'success')
            self.assertFalse((folder/'EXAMPLE.zip.part').exists())
            self.assertTrue(zipfile.is_zipfile(folder/'EXAMPLE.zip'))

    def test_size_limit_cleans_partial_file(self):
        class Context:
            def __init__(self,value): self.value=value
            def __enter__(self): return self.value
            def __exit__(self,*args): pass
        response=SimpleNamespace(status_code=200,headers={'Content-Type':'application/zip'},iter_content=lambda *args:[b'ab',b'cd'])
        session=SimpleNamespace(get=lambda *a,**kw:Context(response))
        with tempfile.TemporaryDirectory() as tmp,patch.object(service.requests,'Session',return_value=Context(session)),patch.object(service,'MAX_FILE',3):
            folder=Path(tmp)
            result=service._fetch({'shipmentNo':'EXAMPLE','downloadUrl':HOST},folder,[0],threading.Lock())
            self.assertEqual(result['status'],'failed')
            self.assertEqual(list(folder.iterdir()),[])
