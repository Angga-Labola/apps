function copyOutput() {
            // Get the text content from the output element
            const textToCopy = document.getElementById('result_container').innerText;
         
            // Use the Clipboard API to copy the text
            navigator.clipboard.writeText(textToCopy).then(() => {
                const status = document.getElementById('copy-status');
                status.innerText = 'Copied!';
                setTimeout(() => { status.innerText = ''; }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
            });

        }

document.getElementById("form").addEventListener("submit", async (e) => {

    e.preventDefault()
    const plain_text = document.getElementById("plain_text").value;
    const result_container = document.getElementById('result_container');
    

    try{
        const response = await fetch('/encryption', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    plain_text: plain_text
                })
            });
        if (!response.ok) throw new Error('Encryption process was not ok');
        const data = await response.json();
        document.getElementById("result_container").innerHTML=`<pre>${data}</pre>` 
    } catch (error) {
        alert('Error encrypting text: ' + error.message);
    } 
})
