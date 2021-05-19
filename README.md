# acts
acts is automation test framework , is open source project in android sourcecode.
is locationed in /tools/test/connectivity/acts/.

acts dont supports app  ui operation  about phone .

this project import uiautomator  add uiautomator property  to android_device.uiautomator.


## new feature uiautomator

android_device add UIautomaotr operation
self.android_device.uiautomator.info
## install 
1.install acts;  refer docs  /tools/test/connectivity/acts/README.md
2.install uiautomator-python
  pip3 install -U uiautomator2
  
## example 
```
class SampleTest(BaseTestClass):
    def setup_class(self):
        self.log.info('Called when the test class is started.')

    def teardown_class(self):
        self.log.info('Called when the test class has finished.')

    def setup_test(self):
        self.log.info('Called before each test case starts.')

    def teardown_test(self):
        self.log.info('Called after each test case completes.')

    """Tests"""

    def test_make_toast(self):
        for ad in self.android_devices:
            self.log.info("test_make_toast")
            ad.uiautomator.press("home")

        return True
```

 
