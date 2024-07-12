pragma solidity ^0.8.0;

contract DocumentVerification {
    mapping(string => bool) private documentHashes;
    mapping(string => address) private documentOwners;

    event DocumentUploaded(string hash);
    event DocumentRevoked(string hash);

    function uploadDocument(string memory hash) public {
        require(!documentHashes[hash], "Document already exists");
        documentHashes[hash] = true;
        documentOwners[hash] = msg.sender;
        emit DocumentUploaded(hash);
    }

    function verifyDocument(string memory hash) public view returns (bool) {
        return documentHashes[hash];
    }

    function revokeDocument(string memory hash) public {
        require(documentHashes[hash], "Document does not exist");
        require(documentOwners[hash] == msg.sender, "Not the owner of the document");
        documentHashes[hash] = false;
        emit DocumentRevoked(hash);
    }
}
