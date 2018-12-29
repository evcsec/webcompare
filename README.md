
# Webcompare

Webcompare is a tool to periodically detect and alert on changes to website content, both visually as well as source changes.

## Getting Started

Currently the tool is in early development stages and is simple to use.

### Prerequisites

Below are the main python libraries and imports currently used for the project. See webcompare.py for full list.

```
- BeautifulSoup4
- requests
- selenium
- Django
- difflib
- arrow
- configparser
- chromedriver
```

### Installing

The script is mostly written to be extremely simple to setup. Running for the first time, or without a config file present will prompt you to set up one or more hosts to scan, and the time interval between each scan.

An interactive prompt can be used to add hosts after-initial setup by using either of the below flags
```
webcompare.py -a
```
*Or*
```
webcompare.py —-addtargets
```

The current list of hosts can also be printed with either of the following
```
webcompare.py -l
```
*Or*
```
webcompare.py —-listtargets
```

Keep in mind host URL’s are validated and thus need to be supplied in the full correct format, including the http:// or https:// prefix.

## Deployment & Alerts

Alerts can be configured to meet any requirements, for my use, the results are being sent via email to a seperate ticketing system.

To set up email alerts, create a file called emailAlert.py in the cloned directory. Feel free to use the template provided below, just make sure you configure it to your needs. For this implementation and testing I'd recommend setting up a spare gmail account.

*emailAlert.py*

```

    import smtplib
    import os
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    
    class EmailAlert:

        def __init__(self):
            pass

        def send_email_alert(self, host_name, soup_diff, visscan_timestamp, detected_change, result_scrn_location):

            before_scrn_location = "./scan_data/mytestpage/scrncompare/"+visscan_timestamp+"/PREV_SCRN_"+visscan_timestamp+".png"

            img_data_before = open(before_scrn_location, 'rb').read()
            image_before = MIMEImage(img_data_before, name=os.path.basename(before_scrn_location))

            img_data_after = open(result_scrn_location, 'rb').read()
            image_after = MIMEImage(img_data_after, name=os.path.basename(result_scrn_location))

            # set the 'from' address,
            fromaddrs = 'youremailaddress@provider.com'
            # set the 'to' addresses,
            # toaddrs = ['recipient@provider.com']
            toaddrs = 'destinationaddress@provider.com'

            msg = MIMEMultipart()
            msg['From'] = fromaddrs
            msg['To'] = toaddrs
            msg['Subject'] = "WebCompare Alert: " + host_name

            body = "Timestamp:* \n" + str(visscan_timestamp) + "\n\n*Visual Scan*\n" + "Detected Visual Change vs previous scan: \n* " + str(detected_change) + "%\n\nSee attached images for visual comparison" + "\n\n*Code Changes*\n"

            for i in soup_diff:
                body += str(i)

            msg.attach(MIMEText(body, 'plain'))

            msg.attach(image_before)
            msg.attach(image_after)

            # setup the email server,
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            # add my account login name and password,
            server.login(fromaddrs, "youremailpassword")

            # Print the email's contents for debugging
            print('From: ' + fromaddrs)
            print('To: ' + str(toaddrs))
            #  pint('Message: ' + str(msg))

            # send the email
            text = msg.as_string()
            server.sendmail(fromaddrs, toaddrs, text)
            # disconnect from the server
            server.quit()


    EmailAlert()

```

## Built With

* [Selenium](https://www.seleniumhq.org/) - Used for visual change detection.

## Authors

* **snags141** - *Initial work*
* **evcsec**
