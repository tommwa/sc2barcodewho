# sc2BarcodeWho

#### This is an early release for early testing, don't expect it to have a high accuracy or be bug free yet. Also, you will probably need to start over and re-load all of your replays in future improved versions if you choose to use this early version.

sc2BarcodeWho is a tool to identify who barcodes are in the game StarCraft 2. 
This tool is designed for pro players since they have thousands of games, 
only a few possible opponents and incentive to use this tool.

The tool works by looking at previous replays to see which player the barcode's behaviour matches.

### Installation + Configuration

Since the users of this tool will have a mix of backgrounds I will try to give additional details on the instructions in expandable form. 
If you already know how to do something you can skip the expandable text. Note that the detailed instructions assume that you use Windows, but other users can also use the program, it will just require some basic computer science skills to translate the instructions to your operating system.

<details><summary>Copy this repository to your computer</summary>


> Easy version: Go to the main page of this repository on GitHub (perhaps just scroll up) and click the <font color="green">green</font> button that says Code and Download zip, then extract unzip it on your computer. That is it. You could for example put it under your user/sc2BarcodeWho. Make sure that the src folder (and README.md) etc is inside here; so user/sc2BarcodeWho/src should exist.


</details>

<details>
<summary>Set up your Python environment with Python 3.10 and the packages given in requirements.txt</summary>

> First, download Python 3.10 from Python's website, for example this  version: https://www.python.org/downloads/release/python-31010/ 
> and scroll down to the installer that matches your operating system (e.g. Windows installer (64-bit). 
> <strong>In the first page on the installation select the box "Add Python.exe to PATH"</strong>; 
> this will allow you to later run commands starting with "python" in the command prompt.
> 
> Second, create a "virtual environment" to separate the python packages from this project.
> This can be done on Windows by opening the Command Prompt (search for it). 
> Once opened, go to the folder for sc2BarcodeWho by typing in cd (which means change directory)
> followed by the path to where you put it, for example
> > cd "C:\Users\replace_with_your_username\sc2BarcodeWho"
> 
> but change it to your path. After pressing enter, this path should be written in the command prompt window ready for your next command.
> From here, we can type 
> > py -m venv scvenv
> 
> which will create the virtual environment called "scvenv". (If you already have other versions of Python installed you can get the correct one for this environment using virtualenv instead of venv, this requires installing virtualenv.)
> After pressing enter, you can see that a folder called "scvenv" has been created inside your sc2BarcodeDecoder folder.
> 
> (If this command did not run, giving a warning like "py is not a recognised command", then you might have forgotten to add Python to your PATH in the Python installation, or you might need to restart your pc. If you added it to PATH and restart and it still does not work google how to add Python to PATH.)
> 
> Now we want to activate this virtual environment, this is simply done by running the activate file in this folder
> > scvenv\Scripts\activate
> 
> After running this, you will see a (scvenv) added to your command prompt text. 
> Great! Your environment is now active, and we can install the required packages on it.
> 
> Keeping the command prompt window that is located in the right folder with the right environment activated, we run
> 
> > py -m pip install -r requirements.txt
>
> This might take a minute or two and will install the packages listed in requirements.txt inside this environment. Your Python setup is now done!
</details>

<details><summary>With your newly set up Python environment, run src/main.py from the command prompt. A basic window with buttons should appear. (+ guide on how to set up a shortcut for it)</summary>

> Now we are ready to try to run the program! 
> 
> In order to run the program we have to first open a command prompt, go to the correct folder and activate the vertual environment that we previously created.
> This is very tedious, so let's create a shortcut to speed it up.
> 
> First, right click your Windows desktop and select "new" -> "shortcut". Type in "cmd.exe" and click next. Then type the name for this shortcut, I suggest "sc2BarcodeWho".
>
> Now this only opens up the command prompt, but we want it to go to the correct folder.
> To achieve this, right-click the shortcut and select "properties".
>  Under the "shortcut" tab you can set the "Start in:" field to the path of the sc2BarcodeWho folder. 
> For me it might be:
> > "C:\Users\FightingFrog\sc2BarcodeWho"
>
> Adjust it to the folder that you put it in.
> Now test the shortcut to see if it indeed writes out this folder when starting the command prompt.
> 
> Next, we want it to automatically activate our virtual environment. 
> To achieve this, again right-click the shortcut and select properties.
> Again under the "shortcut" tab, but this time we are interested in the "Target:" field. Here it might say something like 
> > C:\Windows\System32\cmd.exe
> 
> We want to ADD to this to activate the correct environment using /k and the full path to the activate file. 
> You can open the file explorer, go to sc2BarcodeDecoder, enter the scvenv folder, enter Scripts and copy this path. 
> Also add the "\activate" since this is the script that we want to run to activate the environment.
> It will look something like:<br />
> (don't just copy, remember to switch to your own folder path)
> 
> > C:\Windows\System32\cmd.exe /k "C:\Users\YOUR-USERNAME\sc2BarcodeWho\scvenv\Scripts\activate"
> 
> Again try the shortcut, it should now show that you are in the environment (scvenv).
> 
> Finally, we can run the program by writing into this command prompt 
> 
> python src\main.py
>
> which uses Python to run my main file called main.py.
> This should open a basic GUI window and also keep the command prompt open for output text.
> 
> Finally, optionally, if you want to avoid writing the python src/main.py every time you run the program, you can add it to the shortcut.
> To do this, once again edit the "Target:" and add at the end & python src\main.py, so for example for my folder it looks like:
> 
> > C:\Windows\System32\cmd.exe /k "C:\Users\YOUR-USERNAME\sc2BarcodeWho\scvenv\Scripts\activate" & python src\main.py
> 
> Now when you use this shortcut it will automatically do everything and run the program. 
> So now you can run the program and move on to the next point to test if the program is able to function.
</details>

<details><summary>In the window that opened, click "Set replay folder" and choose the folder where your StarCraft replays are (including sub-folders) I recommend choosing the Accounts folder under your StarCraft II folder. (for example C:\Users\YOUR-USERNAME\Documents\StarCraft II\Accounts)</summary>

![SetReplayFolder](https://user-images.githubusercontent.com/48488386/226102991-fd5410b1-9958-4ea6-b99a-140518a635e9.PNG)
</details>

<details><summary>Now test if everything works as intended. In the window that opened, click "Load all unloaded replays". 
Click the "stop loading replays" button after ~50 replays have been loaded. 
Test if you can then "Classify the most recent replay".</summary>

![LoadAll](https://user-images.githubusercontent.com/48488386/226103034-18de4bc5-0f19-46cd-ab2e-6c09cd84851c.PNG)

![Around50](https://user-images.githubusercontent.com/48488386/226103042-cb046b3e-5013-4afa-911b-9d08cb3f7442.PNG)

![StopLoad](https://user-images.githubusercontent.com/48488386/226103046-9f1e20b8-b8e5-4b87-92dc-71da59679505.PNG)

![ClassifyMostRecent](https://user-images.githubusercontent.com/48488386/226103100-ffac7f63-28ca-4799-a061-063cf247ea27.PNG)
</details>

<details><summary>Now that everything works, choose which replays to load by cleaning up your StarCraft folder.</summary>

> I suggest keeping replay packs + your most recent ~1000 games, for optimal performance you can keep up to maybe 3000 assuming they are all from this year, but it will take longer to set up. Once you moved all older replays to another folder (outside the sc folder) start the program again and load all the replays, this might take around an hour or longer, but you can stop it at any point and progress will be saved for next time.

</details>

### Basic usage

Play a game on ladder, and queue a new game if you want. In the meantime, start this tool with the shortcut created in the installation process and press "classify most recent game" and the result will come out after ~3 seconds as text in the command prompt. I recommend closing the program before your next game since it can take up a lot of RAM memory otherwise. I also recommend using it on non-barcodes to learn which players the tool works on and which players it does not work on.


### Good to know when using

- <strong> Don't trust the result too much. </strong>
- <strong> Note that I intentionally do not take MMR into account in my model </strong>, this is because the human user can better use this information. Therefore, if you play a Protoss with 6.8k mmr then you already know that this can only be one of maybe 3 people, so if the first result is FightingFrog and the second is ShowTime you should guess that it is ShowTime. (self burn). 
- If you play the same barcode player multiple times then every time the model classifies it will do so using only the most recent game. A reason for this sacrifice of information is to prevent people from tricking the model by sharing barcode accounts with other people.
- This tool uses hashing of replays to tell if a replay has previously been loaded, 
this way even if you rename a replay it will not be loaded into the database again. 
But this takes a bit of time when you have thousands of replays, 
so to speed up the process the tool also keeps track of the date of the most recently loaded replay, 
and allows the user to only load replays that are newer than the most recent one. 
This is a good default setting, 
but then you have to remember to change it back when adding replay packs or other older replays. 
This setting if found in the src/config/config.yaml file under "options" -> "LOAD_OLD_REPLAYS" which is set to True or False.
- Since the tool does not know who is using it, it will have to classify both players in a replay including yourself.
But you can tell it to stop classifying yourself by entering your own toon into config.yaml in options -> TOONS_TO_IGNORE.
You can find your own toon by running the program and pressing the "Find Toons" button and selecting a replay that you
are in. You can then write this manually in the src/config/config.yaml file. 
Note that you have a different toon for each account and server.

### Known issues

* StarCraft patches may break the replay parser, which requires manual work to fix. If newer replays can not be parsed, try updating [sc2reader](https://github.com/ggtracker/sc2reader). It might also take some days after a patch until sc2reader will be updated.


### Future possible improvements

<details>
  <summary>Transform tool to a public website</summary>

> The website can be used by anyone with a single quick replay upload without having to install a tool and build up your own replay database which requires a ton of replays and computational time. 
> 
> I already almost implemented this before realizing that storing replay data might violate GDPR. If you are an expert on GDPR and think that I am wrong about this feel free to contact me. 
>> <details>
>>  <summary>Why do I think storing replays might violate GDPR?</summary>
>>
>> Some StarCraft players can be identified (as their real name) using their StarCraft account name which I believe makes it personal information. The "opponent" of a game that a player uploads to the database might not have given permission of this. Additionally, while at first glance the replay data is just silly game data, it contains the date and time which would allow activity logging. Injuries aka health information might be able to be extracted. Also keep in mind that some players are very young. Chat history is also included in the replay. On the other hand, it's possible to throw away many parts of the replay data if that helps. Throwing the data away could even be done on the front-end potentially, so I never get the sensitive data.

</details>
</details>

<details>
  <summary>Higher accuracy</summary>

> There is a lot of potential to make this tool better, it is just a matter of time put in. Currently, I have three completely independent ideas for how to classify, and the end goal is to present results from these three separately. The reason for separate models as opposed to combining their result is that at least two of them can be tricked by tricky players that know how this tool works. Right now only two of these methods are used. With all of these three models it would be a massive waste of time for a pro player to figure out how to trick this tool, if even possible without disrupting their play.
 
</details>

### Acknowledgements

Thank you to the people that made and contributed to [sc2reader](https://github.com/ggtracker/sc2reader). Without it this project would not exist.

### FAQ

<details>
  <summary>Why make this tool?</summary>

>I believe that the StarCraft 2 ladder will become better without anonymous accounts, as this leads to:
>
>More
>* Fun rivalries, chatting, co-operation
>
>Less:
>
>* Toxicity, isolation

</details>

<details>
  <summary>How accurate is it?</summary>

> Firstly, this is an early published version with a lot of unfulfilled potential. 
>
> Secondly, The accuracy depends a lot on how it is used. In order to give you a feel for how accurate the tool is and for which players it works or does not work on, it is recommended to use the tool to identify non-barcode opponents. Then you will see how accurate it is for yourself with your setup!
>
> It works the best if:
>
> - You are a high mmr player that only have a few different opponents on the ladder.
> - You have access to plenty of replays from all the possible opponents on ladder.
> - You use recent replays.
>
> That said, in this basic early release version, when I loaded my most recent ~5000 replays with ~1000 different players the accuracy on average was around 50% when using only 2 replays as training from each player for people within this set of players. Obviously for new players not in the training set the accuracy will always be 0.
</details>

<details>
  <summary>How does it work?</summary>

>This is done by first using a large set of replays to build up a profiles for how each person plays. A barcode is then identified as the player with the most matching feature profile.
>
>The replays are parsed using [sc2reader](https://github.com/ggtracker/sc2reader).
>
>In order to make it more difficult to trick this tool I will not go into detail about what data from the replay is used.

</details>

<details>
  <summary>Who is it for?</summary>

>Top level players only, any region. If you are below GM then you will probably have too many different opponents for this tool to work properly. You might also not get much value out of the tool.

</details>
